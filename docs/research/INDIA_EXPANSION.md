# India representative coverage,12October2026

## Implemented scope
22weather-providerrepresentatives cover19states/UTs in GSI's nationalmapping table. Theoriginalsix IDsandcoordinates remain unchanged. OneadditionalHPpoint coversShimla alongsideMandi. Kerala/TamilNadu/Sikkimuseexistingpoints ratherthan moving themtonewtowncentres.

Source: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2158420

Registry: `backend/ingestion/point_registry_data.py` embeds the versioned source data for serverless imports. `backend/data/representative_points.json` remains a provenance copy, not read at API startup. NewplacesareapproximateGoogleMapsgeocodes, not surveyedfailurelocations. GSIregionalcoverage doesnotproveeachpointisofficiallyhighsusceptibility. No statewide/districtwidewarningcoverageisclaimed.

## Actual descriptivefeatures
Everypointcarriesnearest-native-cellNASAstaticSlope, sourcearchiveURL andoriginalfileSHA256. About0.008333degrees gridspacing, not30msite-slope. Itscoordinate footprint isdeclared. Providerresponseelevation isshownseparately. Theseare descriptivevalues, notnewinputs silentlysubstituted intoNASApretrainedinference.

ActualNASAstaticarchive: https://gpm.nasa.gov/sites/default/files/data/landslides/static.zip

Soildepthnotshownasmeasured. Legacy2017ISRICabsolute-bedrock predictionswereprivatelysampled forfeasibility(7.85-110.16macross19candidates). Thatisnotregolith/failureplanethickness. The2017layerisODbL, notcurrentSoilGrids2CC-BY. Nopublicderivativebedrocktableiscommitted. No inventedcohesion/friction/hydraulicparameter, nofactor-of-safetycomputed.

## Operationalchecks
Providerfetchstillfail-closed andtransactionatomic: allconfiguredpointsmustfetchsuccessfullybeforebatchpersist.22pointson12Octoberreturned200andpassedwindow/unit/nullchecks. Hourlycadenceunchanged. Latest-per-pointSQLwindowrankingpreventsbusypointhistoryfromhidingotherpoints. APIreportsconfiguredcount,availableconfiguredcount,missingcodes and19state/UTscope.

Testscoverpreservedcoordinates,uniquecodes,terrainprovenance,falsewarningflags,rejectedduplicate/fakewarningregistry and110rowhistoryregression. Retrieval isnotindependent groundtruthverification.

## Nextresearchstage
Verifiedlabelledgerfirst.19Aizawlrows are10dates,16recentrows7dates,16approximatecoordinates andmixedtargets. EightRemalsitesareonestorm, notindependentvalidation. NASA2021+global77reports,64rainassociatedafterlabelnormalization,19rainrowscountrymissing. Only3Indiareports. Missingcatalogentriesarenotconfirmedsafe/non-eventdates.

GLaD4CDrecordclaims174eventCSVinformationbutZIPinspectionfoundnoCSVmetadata; onlyalead. Noout-of-countrymodelcalibrationyetcompleted. Existing84eventcomparisonalreadyviewed: itisexploratoryforfuturechanges.

Foriterativetraining,freezecountry/time/storm/event-disjointdevelopment,selection andnewIndiaholdoutbeforeinference. Looponlyondevelopmentfolds. Prespecifyfeatures/calibration/thresholds beforeuntouchedcomparison. Reportalliterations,uncertainty,exclusionsandtiming. Untilverifiednegativeexposure andprospectivelead-timeevaluationexist,nopopulationfailureprobability orpublicwarningclearance.

Physicalmodelroute: https://pubs.usgs.gov/of/2008/1159/ . TRIGRSrequiresactualsite/material/strength/hydrologicparameters; genericsoiltexture cannotcreate them.

## Cold-start and rate-limit hardening
A root-requirements-only environment exposed eager ingestion-package imports requiring optional xarray at API startup. The package now lazy-loads workers; the registry is embedded. CI uses only requirements.txt, unsets DATABASE_URL, imports api.index and calls /api/health. The previous rich research environment masked this dependency.

Hourly provider batches pause7-9seconds between points and retry transient429/5xx/network failures at most3attempts, with jitter. Retry-After above120seconds aborts rather than extending unattended pressure. Invalid/missing payloads remain fail-closed.
