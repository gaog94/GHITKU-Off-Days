# GHITKU-Off-Days
Python Shiny App for Visualizing GHITKU's Off Days

Limitations of the visualization software so far:
- This does not track days off on non-IM blocks (e.g. emergency medicine blocks). Off days during these off-service blocks do not appear on the Amion schedule.
- Days going onto or coming off of night shifts are not tracked as "off" days
- The list of residents is generated based on day 1 of the date range entered. If a resident is not scheduled for a shift (whether working, off, vacation, scheduled, etc.) an Internal-Medicine-Associated service on day 1 of the entered date range, then their schedule will not be available to look at. This typically is only pertinent when looking at schedules for FM/Psych/EM (i.e. non-IM) residents.

Please notify me (Galen) of any bugs or other unanticipated features of the code.

# Attributions
GHITKU-Off-Days is developed and maintained as a personal side-project by Galen Gao.
Internal Medicine PGY2 @ University of Washington Medical Center
