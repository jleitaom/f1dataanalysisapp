# Changelog

All major/notable changes to this project will be documented in this file.

## [1.3.0] - 2025-07-31
### Added
- New tab with Grand Prix overview
  - Round Number
  - Country
  - Location
  - Number of corners
  - Total track distance

## [1.2.0] - 2025-07-30
### Added
- Delta time chart to telemetry tab
- Gear chart to telemetry tab

## [1.1.0] - 2025-07-25
### Added
- Caching mechanism for session data to significantly improve loading times
- App description added to sidebar for better context
- New sidebar structure with:
  - Intuitive info messages to guide users
  - Data loading spinner to clearly indicate data loading status

### Changed
- Major code refactor to improve readability, maintainability and error handling
- Sidebar warning message updated to clearly indicate that data loading can take a few seconds
- Updated app theme colors for aesthetic purposes

### Fixed
- Session types now correctly reflect only those available for the selected Grand Prix format
- Adjusted session results table layout for improved readability
- Fixed driver colors

## [1.0.0] - 2025-01-12
### Added
- Initial public release
- Integrated FastF1 API for F1 data analysis
- Streamlit sidebar controls for year, Grand Prix, and session type
- Interactive sidetabs for:
  - Session results
  - Driver telemetry
  - Tire performance
  - Race strategies