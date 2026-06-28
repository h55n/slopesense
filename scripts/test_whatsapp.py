import asyncio
from dotenv import load_dotenv
load_dotenv()
from backend.alert.alert_engine import AlertEngine
from backend.models import AlertTier
from backend.alert.dispatcher import WhatsAppDispatcher

async def main():
    engine = AlertEngine()
    # Format message simulating an 85% FPI Critical condition
    from datetime import datetime
    alert_dict = {
        "tier": AlertTier.EMERGENCY,
        "block_name": "Kailashahar",
        "district_name": "Unakoti",
        "state_name": "Tripura",
        "fpi_score": 0.85,
        "fpi_ci_lower": 0.75,
        "fpi_ci_upper": 0.95,
        "fpi_24h": 0.90,
        "dominant_signals": [{"signal": "rainfall_accumulation", "value": 0.85}],
        "rainfall_3d_mm": 250,
        "soil_moisture_percentile": 98,
        "issued_at": datetime.utcnow()
    }
    message = engine.format_whatsapp_message(alert=alert_dict, language="en")
    
    dispatcher = WhatsAppDispatcher()
    with open("whatsapp_test_output.txt", "w", encoding="utf-8") as f:
        f.write("--- WhatsApp Message Dispatch Test ---\n")
        f.write("Target Number: +918482984869\n\n")
        f.write("Message Content:\n")
        f.write("-" * 50 + "\n")
        f.write(message + "\n")
        f.write("-" * 50 + "\n")
    print("Check whatsapp_test_output.txt for output.")
    await dispatcher.send_text_message(to="918482984869", message=message)
    print("\nDispatch complete.")

if __name__ == "__main__":
    asyncio.run(main())
