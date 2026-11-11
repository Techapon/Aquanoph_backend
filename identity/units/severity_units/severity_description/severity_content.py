from dataclasses import dataclass


@dataclass(frozen=True)
class SeverityContent:
    detail: str
    guidance: str


# =====================================================================
# SHARED OPTIMAL TEXT
# =====================================================================

_OPTIMAL_DETAIL = "Supports feeding activity and growth in Nile tilapia."
_OPTIMAL_GUIDANCE = "Maintain routine pond management."


# =====================================================================
# DO (LEVEL)
# =====================================================================

DO_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=(
            "Dissolved oxygen is within the suitable range for Nile tilapia. "
            "Fish are likely to breathe normally, feed well, and grow effectively."
        ),
        guidance=(
            "Maintain routine pond management. Check aeration equipment and water quality "
            "to keep DO stable."
        ),
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk low DO. Although the current "
            "DO value has returned to the optimal range, fish may still be stressed, feed less, "
            "and remain vulnerable if water conditions become unstable."
        ),
        guidance=(
            "Keep DO stable and avoid overfeeding. Closely monitor fish behaviour, breathing, "
            "and feeding response."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically low DO. Fish may have accumulated "
            "stress, reduced feeding activity, abnormal swimming behaviour, or reduced disease "
            "resistance even though the current DO value has improved."
        ),
        guidance=(
            "Maintain DO at a good level continuously. Avoid unnecessary disturbance and "
            "overfeeding. Closely monitor fish behaviour and survival."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "Nile tilapia may begin to experience stress from low dissolved oxygen. Possible signs "
            "include increased breathing rate, slower swimming, and reduced feeding. Prolonged "
            "exposure may affect health and growth."
        ),
        guidance=(
            "Check aeration equipment and water circulation. Reduce factors that increase oxygen "
            "demand, such as overfeeding, and monitor DO closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "Nile tilapia have been exposed to low DO continuously beyond the defined threshold. "
            "Stress may become more evident, with slower swimming, increased breathing rate, "
            "reduced feeding, and longer-term health risks."
        ),
        guidance=(
            "Start corrective action promptly. Increase aeration, check water circulation, and "
            "reduce factors that increase oxygen demand."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "Nile tilapia have experienced low DO for multiple periods within 24 hours. Even if "
            "individual events were short, accumulated stress may reduce feeding, weaken fish, "
            "and increase health risks."
        ),
        guidance=(
            "Adjust pond management to reduce repeated low-DO events. Review feeding time and "
            "amount, check aerator operation, and monitor DO during high-risk periods."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "Nile tilapia are exposed to a high-risk low-DO condition. Fish may breathe rapidly, "
            "swim abnormally, or gather near the water surface to access oxygen. Prolonged exposure "
            "may cause serious health effects."
        ),
        guidance=(
            "Take immediate corrective action. Increase aeration, check equipment and water "
            "circulation, temporarily reduce feeding, and monitor DO closely."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "Nile tilapia have been exposed to high-risk low DO continuously beyond the defined "
            "threshold. Stress may become severe, with weakness, laboured breathing, abnormal "
            "swimming, and risk of mortality if not corrected."
        ),
        guidance=(
            "Take emergency action immediately. Increase aeration, stop or reduce feeding, check "
            "aeration equipment, and consider water exchange if necessary."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "Nile tilapia have experienced high-risk low DO for multiple periods within 24 hours. "
            "Although some periods may have improved temporarily, accumulated stress may weaken "
            "fish and increase health risks."
        ),
        guidance=(
            "Adjust pond management immediately. Increase aeration during high-risk periods, reduce "
            "feeding, and investigate repeated causes such as stocking density or water circulation."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "Dissolved oxygen is critically low. Nile tilapia may experience laboured breathing, "
            "weakness, abnormal swimming, and risk of mortality if corrective action is not taken "
            "immediately."
        ),
        guidance=(
            "Take emergency action immediately. Increase aeration, stop feeding temporarily, check "
            "aeration equipment, and consider water exchange or additional oxygenation."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "High-risk low DO has recurred multiple times within 24 hours. Nile tilapia may "
            "experience accumulated stress, weakness, and increased health or mortality risk."
        ),
        guidance=(
            "Take emergency action and investigate the cause of recurrence. Check feeding, aerator "
            "operation, stocking density, and water circulation, then adjust pond management."
        ),
    ),
}


# =====================================================================
# NH3 (LEVEL)
# =====================================================================

NH3_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=_OPTIMAL_DETAIL,
        guidance=_OPTIMAL_GUIDANCE,
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk high NH3. Although the current "
            "NH3 value has returned to the optimal range, fish may still be stressed, feed less, "
            "and remain vulnerable if water quality is unstable."
        ),
        guidance=(
            "Keep NH3 low continuously. Review feeding practices and monitor water quality closely."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically high NH3. Fish may have accumulated "
            "stress, weakness, laboured breathing, or reduced disease resistance even though the "
            "current NH3 value has improved."
        ),
        guidance=(
            "Maintain low NH3 strictly. Avoid overfeeding and closely monitor water quality and "
            "fish health."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "NH3 is above the suitable range and may cause stress in Nile tilapia, including "
            "reduced feeding and reduced activity."
        ),
        guidance=(
            "Monitor water quality, feeding practices, and fish health closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "NH3 has remained above the suitable range continuously. Nile tilapia may experience "
            "ongoing stress and increased health risk."
        ),
        guidance=(
            "Start corrective action promptly. Review feeding practices and water quality management."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "NH3 has been elevated for multiple periods within 24 hours. Nile tilapia may experience "
            "accumulated stress, reduced feeding, and weakness."
        ),
        guidance=(
            "Start corrective action promptly. Adjust feeding and improve water-quality management."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "NH3 is at a high-risk level. Nile tilapia may experience laboured breathing, weakness, "
            "and increased health risk."
        ),
        guidance=(
            "Take immediate action. Review feeding practices and water-quality management."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "NH3 has remained at a high-risk level continuously. Nile tilapia may become weak and "
            "face mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Reduce feeding, check water quality, and consider partial water "
            "exchange."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "NH3 has been at a high-risk level for multiple periods within 24 hours. Nile tilapia may "
            "experience accumulated stress and increased health risk."
        ),
        guidance=(
            "Take immediate action. Adjust feeding, check water quality, and consider partial water "
            "exchange."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "NH3 is critically high. Nile tilapia may experience laboured breathing, weakness, and "
            "risk of mortality if corrective action is not taken immediately."
        ),
        guidance=(
            "Take emergency action immediately. Stop feeding temporarily, check water quality, and "
            "consider partial water exchange."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "High-risk NH3 has recurred multiple times within 24 hours. Nile tilapia may experience "
            "accumulated stress and increased health risk."
        ),
        guidance=(
            "Take immediate action and investigate the cause of recurrence. Check feeding, water "
            "quality, and sludge management."
        ),
    ),
}


# =====================================================================
# NO2-N (LEVEL)
# =====================================================================

NO2_N_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=_OPTIMAL_DETAIL,
        guidance=_OPTIMAL_GUIDANCE,
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk high nitrite. Although the current "
            "value has returned to the optimal range, fish may still be stressed, feed less, and "
            "remain vulnerable if water quality is unstable."
        ),
        guidance=(
            "Keep nitrite low continuously. Review feeding practices and monitor water quality closely."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically high nitrite. Fish may have accumulated "
            "stress, weakness, laboured breathing, or reduced disease resistance even though the "
            "current value has improved."
        ),
        guidance=(
            "Maintain low nitrite strictly. Avoid overfeeding and closely monitor water quality and "
            "fish health."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "Nitrite is above the suitable range and may cause stress in Nile tilapia, including "
            "reduced feeding and reduced activity."
        ),
        guidance=(
            "Monitor water quality, feeding practices, and fish health closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "Nitrite has remained above the suitable range continuously. Nile tilapia may experience "
            "ongoing stress and increased health risk."
        ),
        guidance=(
            "Start corrective action promptly. Review feeding practices and water-quality management."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "Nitrite has been elevated for multiple periods within 24 hours. Nile tilapia may experience "
            "accumulated stress, reduced feeding, and weakness."
        ),
        guidance=(
            "Start corrective action promptly. Adjust feeding and improve water-quality management."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "Nitrite is at a high-risk level. Nile tilapia may experience laboured breathing, weakness, "
            "and increased health risk."
        ),
        guidance=(
            "Take immediate action. Review feeding practices and water-quality management."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "Nitrite has remained at a high-risk level continuously. Nile tilapia may become weak and "
            "face mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Reduce feeding, check water quality, and consider partial water "
            "exchange."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "Nitrite has been at a high-risk level for multiple periods within 24 hours. Nile tilapia may "
            "experience accumulated stress and increased health risk."
        ),
        guidance=(
            "Take immediate action. Adjust feeding, check water quality, and consider partial water "
            "exchange."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "Nitrite is critically high. Nile tilapia may experience laboured breathing, weakness, and "
            "risk of mortality if corrective action is not taken immediately."
        ),
        guidance=(
            "Take emergency action immediately. Stop feeding temporarily, check water quality, and "
            "consider partial water exchange."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "High-risk nitrite has recurred multiple times within 24 hours. Nile tilapia may experience "
            "accumulated stress and increased health risk."
        ),
        guidance=(
            "Take immediate action and investigate the cause of recurrence. Check feeding, water "
            "quality, and sludge management."
        ),
    ),
}


# =====================================================================
# SALINITY (LEVEL)
# =====================================================================

SALINITY_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=_OPTIMAL_DETAIL,
        guidance=_OPTIMAL_GUIDANCE,
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk high salinity. Although the current "
            "value has returned to the optimal range, fish may still be stressed, feed less, and remain "
            "vulnerable if water conditions are unstable."
        ),
        guidance=(
            "Maintain salinity within the suitable range continuously. Monitor water source and fish health."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically high salinity. Fish may have accumulated "
            "stress, weakness, laboured breathing, or reduced disease resistance even though the current "
            "value has improved."
        ),
        guidance=(
            "Maintain salinity within the suitable range strictly. Avoid sudden water-quality changes and "
            "closely monitor fish health."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "Salinity is above the suitable range and may cause stress in Nile tilapia, including reduced "
            "feeding and reduced activity."
        ),
        guidance=(
            "Monitor water source, water-quality management, and fish health closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "Salinity has remained above the suitable range continuously. Nile tilapia may experience "
            "ongoing stress and increased health risk."
        ),
        guidance=(
            "Start corrective action promptly. Check the water source and water-management practices."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "Salinity has been elevated for multiple periods within 24 hours. Nile tilapia may experience "
            "accumulated stress, reduced feeding, and weakness."
        ),
        guidance=(
            "Start corrective action promptly. Review water source and water-management practices."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "Salinity is at a high-risk level. Nile tilapia may experience laboured breathing, weakness, "
            "and increased health risk."
        ),
        guidance=(
            "Take immediate action. Check the water source and water-management practices."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "Salinity has remained at a high-risk level continuously. Nile tilapia may become weak and "
            "face mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Check the water source, reduce feeding, and consider partial water "
            "exchange."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "Salinity has been at a high-risk level for multiple periods within 24 hours. Nile tilapia may "
            "experience accumulated stress and increased health risk."
        ),
        guidance=(
            "Take immediate action. Review water source, water management, and consider partial water "
            "exchange."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "Salinity is critically high. Nile tilapia may experience laboured breathing, weakness, and "
            "risk of mortality if corrective action is not taken immediately."
        ),
        guidance=(
            "Take emergency action immediately. Stop feeding temporarily, check the water source, and "
            "consider partial water exchange."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "High-risk salinity has recurred multiple times within 24 hours. Nile tilapia may experience "
            "accumulated stress and increased health risk."
        ),
        guidance=(
            "Take immediate action and investigate the cause of recurrence. Check the water source, "
            "feeding practices, and water management."
        ),
    ),
}


# =====================================================================
# pH (RANGE) — LOW
# =====================================================================

PH_LOW_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=_OPTIMAL_DETAIL,
        guidance=_OPTIMAL_GUIDANCE,
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk low pH. Although the current pH value "
            "has returned to the optimal range, fish may still be stressed by water-quality changes and "
            "remain vulnerable."
        ),
        guidance=(
            "Maintain pH within the suitable range continuously. Monitor water stability and fish health."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically low pH. Fish may have accumulated stress, "
            "weakness, or tissue and health effects even though the current pH value has improved."
        ),
        guidance=(
            "Maintain pH within the suitable range strictly. Avoid sudden water-quality changes and "
            "closely monitor fish health."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "pH is below the suitable range and may stress Nile tilapia due to changing water conditions."
        ),
        guidance=(
            "Monitor water stability and fish health closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "pH has remained below the suitable range continuously. Nile tilapia may experience ongoing "
            "stress from changing water conditions."
        ),
        guidance=(
            "Start corrective action promptly. Monitor water stability and fish health closely."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "pH has been below the suitable range for multiple periods within 24 hours. Nile tilapia may "
            "experience accumulated stress from changing water conditions."
        ),
        guidance=(
            "Start corrective action promptly. Monitor water stability and fish health closely."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "pH is at a high-risk low level. Nile tilapia may be at risk of tissue damage and health effects."
        ),
        guidance=(
            "Take immediate action. Monitor water stability and fish health closely."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "pH has remained at a high-risk low level continuously. Nile tilapia may face mortality risk "
            "if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor water stability and fish health closely."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "pH has been at a high-risk low level for multiple periods within 24 hours. Nile tilapia may "
            "face mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor water stability and fish health closely."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "pH is critically low. Nile tilapia may face mortality risk if corrective action is not taken "
            "immediately."
        ),
        guidance=(
            "Take immediate action. Monitor water stability and fish health closely."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "Low pH has recurred multiple times. Nile tilapia may face mortality risk if the condition "
            "is not corrected."
        ),
        guidance=(
            "Take immediate action and investigate the cause of recurrence. Monitor water stability and "
            "fish health closely."
        ),
    ),
}


# =====================================================================
# pH (RANGE) — HIGH
# =====================================================================

PH_HIGH_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=_OPTIMAL_DETAIL,
        guidance=_OPTIMAL_GUIDANCE,
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk high pH. Although the current pH value "
            "has returned to the optimal range, fish may still be stressed and remain vulnerable to "
            "increased NH3 toxicity."
        ),
        guidance=(
            "Maintain pH within the suitable range continuously. Monitor NH3 toxicity risk closely."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically high pH. Fish may have accumulated stress, "
            "weakness, or increased exposure to toxic NH3 even though the current pH value has improved."
        ),
        guidance=(
            "Maintain pH within the suitable range strictly. Avoid sudden water-quality changes and monitor "
            "NH3 toxicity risk closely."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "pH is above the suitable range and may increase the toxic fraction of NH3."
        ),
        guidance=(
            "Monitor NH3 toxicity risk closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "pH has remained above the suitable range continuously. NH3 may become more toxic to Nile tilapia."
        ),
        guidance=(
            "Start corrective action promptly. Monitor NH3 toxicity risk closely."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "pH has been above the suitable range for multiple periods within 24 hours. NH3 may become more "
            "toxic to Nile tilapia."
        ),
        guidance=(
            "Start corrective action promptly. Monitor NH3 toxicity risk closely."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "pH is at a high-risk high level. Nile tilapia may be at risk of tissue damage and health effects."
        ),
        guidance=(
            "Take immediate action. Monitor NH3 toxicity risk closely."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "pH has remained at a high-risk high level continuously. Nile tilapia may face mortality risk "
            "if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor NH3 toxicity risk closely."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "pH has been at a high-risk high level for multiple periods within 24 hours. Nile tilapia may "
            "face mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor NH3 toxicity risk closely."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "pH is critically high. Nile tilapia may face mortality risk if corrective action is not taken "
            "immediately."
        ),
        guidance=(
            "Take immediate action. Monitor NH3 toxicity risk closely."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "High pH has recurred multiple times. Nile tilapia may face mortality risk if the condition "
            "is not corrected."
        ),
        guidance=(
            "Take immediate action and investigate the cause of recurrence. Monitor NH3 toxicity risk closely."
        ),
    ),
}


# =====================================================================
# TEMPERATURE (RANGE) — LOW
# =====================================================================

TEMPERATURE_LOW_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=_OPTIMAL_DETAIL,
        guidance=_OPTIMAL_GUIDANCE,
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk low water temperature. Although the "
            "current temperature has returned to the optimal range, fish may still be stressed, feed less, "
            "and remain vulnerable."
        ),
        guidance=(
            "Maintain water temperature within the suitable range continuously. Monitor feeding activity "
            "and fish health."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically low water temperature. Fish may have "
            "accumulated stress, weakness, reduced feeding, or reduced disease resistance even though the "
            "current temperature has improved."
        ),
        guidance=(
            "Maintain water temperature within the suitable range strictly. Avoid sudden temperature changes "
            "and closely monitor fish health."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "Water temperature is below the suitable range and may stress Nile tilapia, reducing feeding "
            "and activity."
        ),
        guidance=(
            "Monitor water temperature and fish health closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "Water temperature has remained below the suitable range continuously. Nile tilapia may "
            "experience ongoing stress from changing water conditions."
        ),
        guidance=(
            "Start corrective action promptly. Monitor water temperature and fish health closely."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "Water temperature has been below the suitable range for multiple periods within 24 hours. "
            "Nile tilapia may experience accumulated stress from changing water conditions."
        ),
        guidance=(
            "Start corrective action promptly. Monitor water temperature and fish health closely."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "Water temperature is at a high-risk low level. Nile tilapia may be at risk of reduced health "
            "and growth."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature and fish health closely."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "Water temperature has remained at a high-risk low level continuously. Nile tilapia may face "
            "mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature and fish health closely."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "Water temperature has been at a high-risk low level for multiple periods within 24 hours. "
            "Nile tilapia may face mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature and fish health closely."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "Water temperature is critically low. Nile tilapia may face mortality risk if corrective action "
            "is not taken immediately."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature and fish health closely."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "Low water temperature has recurred multiple times. Nile tilapia may face mortality risk if "
            "the condition is not corrected."
        ),
        guidance=(
            "Take immediate action and investigate the cause of recurrence. Monitor water temperature and "
            "fish health closely."
        ),
    ),
}


# =====================================================================
# TEMPERATURE (RANGE) — HIGH
# =====================================================================

TEMPERATURE_HIGH_CONTENT = {
    "pureOptimal": SeverityContent(
        detail=_OPTIMAL_DETAIL,
        guidance=_OPTIMAL_GUIDANCE,
    ),

    "needRocoveryEleveted": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced elevated-risk high water temperature. Although the "
            "current temperature has returned to the optimal range, fish may still be stressed, feed less, "
            "and remain vulnerable to increased oxygen demand."
        ),
        guidance=(
            "Maintain water temperature within the suitable range continuously. Monitor DO and fish health."
        ),
    ),

    "needRocoveryCritical": SeverityContent(
        detail=(
            "Nile tilapia have recently experienced critically high water temperature. Fish may have "
            "accumulated stress, weakness, laboured breathing, or increased vulnerability to low DO even "
            "though the current temperature has improved."
        ),
        guidance=(
            "Maintain water temperature within the suitable range strictly. Avoid sudden temperature changes "
            "and monitor DO and fish health closely."
        ),
    ),

    "pureStress": SeverityContent(
        detail=(
            "Water temperature is above the suitable range and may stress Nile tilapia, reducing feeding "
            "and activity."
        ),
        guidance=(
            "Monitor water temperature, DO, and fish health closely."
        ),
    ),

    "continuousStressExceeded": SeverityContent(
        detail=(
            "Water temperature has remained above the suitable range continuously. Nile tilapia may "
            "experience ongoing stress from changing water conditions."
        ),
        guidance=(
            "Start corrective action promptly. Monitor water temperature, DO, and fish health closely."
        ),
    ),

    "cumStressExceeded": SeverityContent(
        detail=(
            "Water temperature has been above the suitable range for multiple periods within 24 hours. "
            "Nile tilapia may experience accumulated stress from changing water conditions."
        ),
        guidance=(
            "Start corrective action promptly. Monitor water temperature, DO, and fish health closely."
        ),
    ),

    "pureHighRisk": SeverityContent(
        detail=(
            "Water temperature is at a high-risk high level. Nile tilapia may be at risk of reduced health "
            "and growth."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature, DO, and fish health closely."
        ),
    ),

    "continuousHighRiskExceeded": SeverityContent(
        detail=(
            "Water temperature has remained at a high-risk high level continuously. Nile tilapia may face "
            "mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature, DO, and fish health closely."
        ),
    ),

    "cumHighRiskExceeded": SeverityContent(
        detail=(
            "Water temperature has been at a high-risk high level for multiple periods within 24 hours. "
            "Nile tilapia may face mortality risk if the condition is not corrected."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature, DO, and fish health closely."
        ),
    ),

    "pureCritical": SeverityContent(
        detail=(
            "Water temperature is critically high. Nile tilapia may face mortality risk if corrective action "
            "is not taken immediately."
        ),
        guidance=(
            "Take immediate action. Monitor water temperature, DO, and fish health closely."
        ),
    ),

    "episodeExceeded": SeverityContent(
        detail=(
            "High water temperature has recurred multiple times. Nile tilapia may face mortality risk if "
            "the condition is not corrected."
        ),
        guidance=(
            "Take immediate action and investigate the cause of recurrence. Monitor water temperature, DO, "
            "and fish health closely."
        ),
    ),
}