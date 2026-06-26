"""
SlopeSense — Alert Engine

Converts block-level FPI scores into actionable alerts.

Logic:
  1. Threshold evaluation per block (WATCH / WARNING / EMERGENCY)
  2. Temporal persistence: WARNING tier requires 2 consecutive cycles (12h)
     before WhatsApp fires. EMERGENCY fires immediately.
  3. Confidence gating: alerts suppressed when CI width > 0.30
  4. Spatial clustering: already applied in FPIEngine.aggregate_to_blocks()
  5. De-duplication: don't re-alert if already active with same tier
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from backend.alert.verifier import LLMVerifier

logger = logging.getLogger(__name__)

# Alert tier actions (for display and message generation)
TIER_ACTIONS = {
    "WATCH": {
        "en": "Alert DDMA. Monitor situation. Pre-notify Gram Pradhan near slopes.",
        "hi": "DDMA को सूचित करें। स्थिति पर नज़र रखें। ढलान के पास ग्राम प्रधान को सूचित करें।",
        "ml": "DDMA-യെ അറിയിക്കുക. സ്ഥിതി നിരീക്ഷിക്കുക.",
        "kn": "DDMA ಗೆ ತಿಳಿಸಿ. ಪರಿಸ್ಥಿತಿ ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿ.",
        "mr": "DDMA ला सूचित करा. परिस्थिती निरीक्षण करा.",
        "bn": "DDMA-কে জানান। পরিস্থিতি পর্যবেক্ষণ করুন।",
        "ta": "DDMA-வை தெரிவிக்கவும். நிலைமையை கண்காணிக்கவும்.",
    },
    "WARNING": {
        "en": "Alert SDMA + DDMA. Pre-position NDRF/SDRF. Issue public advisory. Pre-evacuate highest-risk households.",
        "hi": "SDMA + DDMA को अलर्ट करें। NDRF/SDRF को तैनात करें। सार्वजनिक सलाह जारी करें।",
        "ml": "SDMA + DDMA-യ്ക്ക് അലർട്ട്. NDRF/SDRF-നെ നിയോഗിക്കുക.",
        "kn": "SDMA + DDMA ಗೆ ಎಚ್ಚರಿಕೆ. NDRF/SDRF ನಿಯೋಜಿಸಿ.",
        "mr": "SDMA + DDMA ला इशारा. NDRF/SDRF तैनात करा.",
        "bn": "SDMA + DDMA-কে সতর্ক করুন। NDRF/SDRF মোতায়েন করুন।",
        "ta": "SDMA + DDMA-வை எச்சரிக்கவும். NDRF/SDRF-ஐ நிலைநிறுத்தவும்.",
    },
    "EMERGENCY": {
        "en": "IMMEDIATE EVACUATION ADVISORY. All channels activated. NDRF deployment authorized.",
        "hi": "तत्काल निकासी सलाह। सभी चैनल सक्रिय। NDRF तैनाती अधिकृत।",
        "ml": "ഉടനടി ഒഴിപ്പിക്കൽ നിർദ്ദേശം. എല്ലാ ചാനലുകളും സജീവം.",
        "kn": "ತಕ್ಷಣದ ಸ್ಥಳಾಂತರ ಸಲಹೆ. ಎಲ್ಲಾ ಚಾನಲ್‌ಗಳು ಸಕ್ರಿಯ.",
        "mr": "तत्काळ निर्वासन सूचना. सर्व माध्यमे कार्यरत.",
        "bn": "তাৎক্ষণিক সরিয়ে নেওয়ার পরামর্শ। সব চ্যানেল সক্রিয়।",
        "ta": "உடனடி வெளியேற்ற அறிவுரை. அனைத்து சேனல்களும் செயல்படுகின்றன.",
    },
}

TIER_EMOJI = {
    "WATCH":     "🟡",
    "WARNING":   "🔴",
    "EMERGENCY": "🆘",
    "MONITORING": "🔵",
}


class AlertEngine:
    """
    Converts block-level FPI results into Alert objects and determines
    which alerts should trigger immediate notification.
    """

    def __init__(self, db_session=None):
        self.db = db_session
        self.verifier = LLMVerifier()

    async def evaluate_blocks(
        self,
        block_fpis: List,  # List[BlockFPI]
        previous_alerts: Optional[Dict[str, Dict]] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Evaluate block FPIs against thresholds.

        Args:
            block_fpis: list of BlockFPI from model engine
            previous_alerts: dict of block_code → previous alert state
                             (for temporal persistence check)

        Returns:
            (new_alerts, expired_alerts) — dicts ready for DB insert
        """
        if previous_alerts is None:
            previous_alerts = {}

        new_alerts = []
        expired_alerts = []

        for block in block_fpis:
            tier = block.alert_tier
            prev = previous_alerts.get(block.block_code)

            # Skip NORMAL and MONITORING for alert creation
            if tier in ("NORMAL", "MONITORING"):
                # If there was a previous active alert, expire it
                if prev and prev.get("is_active"):
                    expired_alerts.append({
                        "block_code": block.block_code,
                        "cleared_at": block.run_timestamp,
                    })
                continue

            # Temporal persistence check
            consecutive = 1
            if prev:
                if prev.get("tier") == tier:
                    consecutive = prev.get("consecutive_cycles", 1) + 1
                elif tier == "EMERGENCY":
                    consecutive = 1  # emergency always fires immediately

            # Should WhatsApp fire?
            should_notify = (
                tier == "EMERGENCY" or  # always immediate
                (tier == "WARNING" and consecutive >= 2) or
                (tier == "WATCH" and consecutive >= 3)
            )

            alert = {
                "id": str(uuid.uuid4()),
                "alert_code": f"{block.state_code}_{block.district_code}_{block.block_code}_{int(block.run_timestamp.timestamp())}",
                "state_code": block.state_code,
                "state_name": block.state_name,
                "district_code": block.district_code,
                "district_name": block.district_name,
                "block_code": block.block_code,
                "block_name": block.block_name,
                "fpi_score": block.fpi_score,
                "fpi_ci_lower": block.fpi_ci_lower,
                "fpi_ci_upper": block.fpi_ci_upper,
                "fpi_24h": block.fpi_24h,
                "cell_count_total": block.cell_count_total,
                "cell_count_breached": block.cell_count_breached,
                "breach_fraction": block.breach_fraction,
                "tier": tier,
                "is_active": True,
                "is_suppressed": block.is_suppressed,
                "consecutive_cycles": consecutive,
                "dominant_signals": block.dominant_signals,
                "rainfall_3d_mm": block.rainfall_3d_mm,
                "soil_moisture_percentile": block.soil_moisture_pct,
                "issued_at": block.run_timestamp,
                "should_notify": should_notify,
            }
            
            # AGENT 2: Audit the alert if it's high risk
            if tier in ("WARNING", "EMERGENCY"):
                approved, reason = await self.verifier.verify(alert)
                if not approved:
                    alert["is_suppressed"] = True
                    alert["should_notify"] = False
                    logger.warning(f"Alert {alert['alert_code']} suppressed by Auditor: {reason}")
                else:
                    logger.info(f"Alert {alert['alert_code']} approved by Auditor: {reason}")

            new_alerts.append(alert)

        logger.info(
            f"Alert engine: {len(new_alerts)} active alerts, "
            f"{sum(1 for a in new_alerts if a['should_notify'])} to notify, "
            f"{len(expired_alerts)} expired"
        )
        return new_alerts, expired_alerts

    def format_whatsapp_message(
        self,
        alert: Dict,
        language: str = "hi",
    ) -> str:
        """
        Format WhatsApp alert message in target language.

        Includes:
        - Emoji tier indicator
        - Location
        - Risk level (% and label)
        - 24h forecast
        - Top signals
        - Recommended action
        - Source and timestamp
        """
        tier = alert["tier"]
        emoji = TIER_EMOJI.get(tier, "⚠️")
        fpi_pct = int(alert["fpi_score"] * 100)
        fpi_24h_pct = int((alert.get("fpi_24h") or alert["fpi_score"]) * 100)

        # Build signal description
        signals = alert.get("dominant_signals", [])
        signal_text = ""
        if signals:
            s = signals[0]
            sig_name = s.get("signal", "").replace("_", " ").title()
            signal_text = f"{sig_name}"

        rain_mm = alert.get("rainfall_3d_mm", 0)
        sm_pct = alert.get("soil_moisture_percentile", 0)

        if language == "hi":
            tier_label = {"WATCH": "मध्यम", "WARNING": "उच्च", "EMERGENCY": "बहुत उच्च"}.get(tier, tier)
            action = TIER_ACTIONS.get(tier, {}).get("hi", "")
            timestamp = alert["issued_at"].strftime("%d %B, %H:%M IST") if hasattr(alert["issued_at"], "strftime") else str(alert["issued_at"])
            msg = (
                f"{emoji} SLOPESENSE {tier_label.upper()} चेतावनी\n"
                f"जिला: {alert['district_name']} | ब्लॉक: {alert['block_name']}\n\n"
                f"जोखिम स्तर: {tier_label} ({fpi_pct}%)\n"
                f"अगले 24 घंटे: {fpi_24h_pct}%\n"
                f"3-दिन वर्षा: {rain_mm:.0f}mm | मिट्टी नमी: {sm_pct:.0f}वीं प्रतिशत\n\n"
                f"⚡ सिफारिश: {action}\n\n"
                f"स्रोत: SlopeSense | NDMA डेटा\n"
                f"अपडेट: {timestamp}"
            )
        elif language == "ml":
            tier_label = {"WATCH": "മിതമായ", "WARNING": "ഉയർന്ന", "EMERGENCY": "അതി ഉയർന്ന"}.get(tier, tier)
            action = TIER_ACTIONS.get(tier, {}).get("ml", "")
            msg = (
                f"{emoji} SLOPESENSE {tier_label.upper()} മുന്നറിയിപ്പ്\n"
                f"ജില്ല: {alert['district_name']} | ബ്ലോക്ക്: {alert['block_name']}\n\n"
                f"അപകട നില: {tier_label} ({fpi_pct}%)\n"
                f"അടുത്ത 24 മണിക്കൂർ: {fpi_24h_pct}%\n"
                f"3 ദിവസ മഴ: {rain_mm:.0f}mm | മണ്ണ് ഈർപ്പം: {sm_pct:.0f}th percentile\n\n"
                f"⚡ നിർദ്ദേശം: {action}\n\n"
                f"ഉറവിടം: SlopeSense | NDMA Data"
            )
        else:
            # English default
            tier_label = {"WATCH": "ELEVATED", "WARNING": "HIGH", "EMERGENCY": "CRITICAL"}.get(tier, tier)
            action = TIER_ACTIONS.get(tier, {}).get("en", "")
            timestamp = alert["issued_at"].strftime("%d %b %Y, %H:%M UTC") if hasattr(alert["issued_at"], "strftime") else str(alert["issued_at"])
            msg = (
                f"{emoji} SLOPESENSE {tier_label} RISK ALERT\n"
                f"District: {alert['district_name']} | Block: {alert['block_name']}\n\n"
                f"Risk Level: {tier_label} ({fpi_pct}%) — CI: {int(alert['fpi_ci_lower']*100)}–{int(alert['fpi_ci_upper']*100)}%\n"
                f"24h Forecast: {fpi_24h_pct}%\n"
                f"3-day Rainfall: {rain_mm:.0f}mm | Soil Moisture: {sm_pct:.0f}th pct\n\n"
                f"⚡ Action: {action}\n\n"
                f"Source: SlopeSense v0.1 | NASA GPM + SMAP + NDMA\n"
                f"Updated: {timestamp}"
            )

        return msg

    def format_cap_xml(self, alert: Dict, base_url: str = "https://api.slopesense.in") -> str:
        """
        Format alert as CAP v1.2 XML.
        Compatible with NDMA Sachet app and any CAP consumer.
        """
        from xml.sax.saxutils import escape

        tier = alert["tier"]
        fpi_pct = int(alert["fpi_score"] * 100)
        urgency = {"WATCH": "Future", "WARNING": "Expected", "EMERGENCY": "Immediate"}.get(tier, "Unknown")
        severity = {"WATCH": "Minor", "WARNING": "Moderate", "EMERGENCY": "Extreme"}.get(tier, "Unknown")
        certainty = {"WATCH": "Possible", "WARNING": "Likely", "EMERGENCY": "Observed"}.get(tier, "Unknown")

        issued = alert["issued_at"].strftime("%Y-%m-%dT%H:%M:%S+00:00") if hasattr(alert["issued_at"], "strftime") else str(alert["issued_at"])

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>{escape(alert['alert_code'])}</identifier>
  <sender>SlopeSense-v0.1@slopesense.in</sender>
  <sent>{issued}</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <note>SlopeSense Landslide Risk Alert — Failure Probability Index</note>
  <info>
    <language>en-IN</language>
    <category>Geo</category>
    <event>Landslide Risk — {tier}</event>
    <urgency>{urgency}</urgency>
    <severity>{severity}</severity>
    <certainty>{certainty}</certainty>
    <headline>Landslide Risk Alert: {escape(alert['district_name'])}, {escape(alert['state_name'])} — FPI {fpi_pct}%</headline>
    <description>SlopeSense Failure Probability Index: {fpi_pct}% ({tier}). Block: {escape(alert['block_name'])}. 3-day rainfall: {alert.get('rainfall_3d_mm', 0):.0f}mm. Soil moisture: {alert.get('soil_moisture_percentile', 0):.0f}th percentile. 24h forecast FPI: {int((alert.get('fpi_24h') or alert['fpi_score']) * 100)}%.</description>
    <instruction>{TIER_ACTIONS.get(tier, {}).get('en', '')}</instruction>
    <web>{base_url}/dashboard?district={escape(alert['district_code'])}</web>
    <parameter>
      <valueName>FPI_Score</valueName>
      <value>{alert['fpi_score']}</value>
    </parameter>
    <parameter>
      <valueName>FPI_CI_Lower</valueName>
      <value>{alert['fpi_ci_lower']}</value>
    </parameter>
    <parameter>
      <valueName>FPI_CI_Upper</valueName>
      <value>{alert['fpi_ci_upper']}</value>
    </parameter>
    <parameter>
      <valueName>Rainfall_3day_mm</valueName>
      <value>{alert.get('rainfall_3d_mm', 0)}</value>
    </parameter>
    <area>
      <areaDesc>{escape(alert['block_name'])}, {escape(alert['district_name'])}, {escape(alert['state_name'])}</areaDesc>
    </area>
  </info>
</alert>"""
        return xml
