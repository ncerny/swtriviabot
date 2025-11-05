# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Image URL Hiding Feature**: Images in trivia questions are now displayed using Discord embeds, hiding URLs from chat for cleaner appearance
  - Added `Image` model for URL validation and metadata
  - Added `ImageService` for async image validation and embed creation
  - Modified `/post-question` command to use embeds instead of raw URLs
  - Added comprehensive unit and integration tests
  - Supports JPEG, PNG, GIF, and WebP formats up to 8MB

### Technical Improvements
- Enhanced error handling for image validation with user-friendly messages
- Added async image processing to maintain bot responsiveness
- Improved separation of concerns with dedicated image service
