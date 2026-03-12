# Changelog

All notable changes to Project Gorgon VIP StorageBuddy will be documented in this file.

## [0.7.2] - 2026-03-12

### Added
- Multi-character support in overlay with character selection sync
- Empty state message when no character is selected in overlay
- `is_completable` and `is_purchasable` flags in overlay API for Ready filter

### Fixed
- Overlay "disconnected" error caused by vendor data type mismatch
- Character selection sync between main page and overlay popup
- Vendor data handling for mixed dict/string formats in API responses

### Changed
- Overlay now reads character selection from localStorage on each refresh cycle
- Updated documentation for overlay character sync behavior

## [0.7.1] - 2026-03-12

### Fixed
- Consistent wiki links across all views
- Region filter functionality

## [0.7.0] - 2026-03-11

### Added
- Unified overlay materials view with storage locations
- Aggregated materials display in overlay

## [0.6.9] - 2026-03-10

### Changed
- Unified visual consistency across Quest and Crafting views

## [0.6.8] - 2026-03-10

### Added
- Full theme support across all UI elements

## [0.6.7] - 2026-03-10

### Fixed
- Missing inventory items in Ready Quests storage display

## [0.6.6] - 2026-03-09

### Changed
- Improved Ready Quests layout with table-based alignment

## [0.6.5] - 2026-03-09

### Added
- High contrast theme for accessibility
- Improved Ready view layout

## [0.6.4] - 2026-03-08

### Added
- Enhanced Quest Checklist with storage locations

## [0.6.3] - 2026-03-08

### Added
- Item resolution service
- UI improvements

## [0.6.2] - 2026-03-08

### Changed
- Major architecture refactoring
- Security hardening

## [0.6.1] - 2026-03-07

### Added
- Theme system with 7 color themes
- Quest pinning functionality
- Favor API integration
