# Velocitas Extension - Modular Bundling Architecture

## Overview

The Velocitas extension has been restructured with a modern modular bundling system inspired by the inboxy project. This architecture provides better code organization, maintainability, and bundling efficiency.

## Project Structure

```
extension/
├── src/                          # Source code (modular)
│   ├── content.js               # Main entry point
│   ├── bundling/                # Email bundling logic
│   │   ├── DateGrouper.js       # Date-based email grouping
│   │   └── BundleToggler.js     # Bundle interaction handling
│   ├── components/              # Reusable UI components
│   ├── containers/              # Data container classes
│   │   ├── Bundle.js            # Bundle container
│   │   └── BundledMail.js       # Bundle management
│   ├── handlers/                # Event handlers and observers
│   │   ├── MainParentObserver.js
│   │   ├── MessageListObserver.js
│   │   └── MessageListWatcher.js
│   └── util/                    # Utilities and constants
│       ├── Constants.js         # Application constants
│       └── DomUtils.js          # DOM manipulation utilities
├── test/                        # Test files
│   └── DateGrouper.test.js
├── dist/                        # Built/bundled output
│   └── content.js              # Webpack bundled file
├── package.json                 # Dependencies and scripts
├── webpack.config.js            # Webpack configuration
├── .babelrc                     # Babel configuration
├── build.sh                     # Build automation script
├── manifest.json                # Chrome extension manifest
├── popup.html                   # Extension popup
├── styles.css                   # CSS styles
└── icons/                       # Extension icons
```

## Key Features

### 1. Modular Architecture
- **Separation of Concerns**: Each module handles a specific responsibility
- **Reusability**: Components can be easily reused across the extension
- **Maintainability**: Clear structure makes code easier to understand and modify

### 2. Modern Build System
- **Webpack Bundling**: Efficient module bundling with tree shaking
- **Babel Transformation**: ES6+ support with backwards compatibility
- **Source Maps**: Development debugging support
- **Automated Build**: Single command builds and packages the extension

### 3. Component Organization

#### Bundling (`src/bundling/`)
- `DateGrouper.js`: Groups emails by date categories (Today, Yesterday, etc.)
- `BundleToggler.js`: Handles opening/closing of email bundles

#### Containers (`src/containers/`)
- `Bundle.js`: Represents a group of related emails
- `BundledMail.js`: Manages all email bundles and their state

#### Handlers (`src/handlers/`)
- `MainParentObserver.js`: Watches for major Gmail DOM changes
- `MessageListObserver.js`: Observes email list specific changes
- `MessageListWatcher.js`: Coordinates message list observations

#### Utilities (`src/util/`)
- `Constants.js`: Centralized constants and selectors
- `DomUtils.js`: DOM manipulation and email data extraction utilities

## Development Workflow

### Prerequisites
```bash
npm install
```

### Development Commands

#### Build for Production
```bash
npm run build
# or
./build.sh
```

#### Development Mode (with file watching)
```bash
npm run dev
```

#### Run Tests
```bash
npm test
```

### Build Process

1. **Webpack Bundling**: All ES6 modules are bundled into a single `content.js`
2. **Babel Transformation**: ES6+ code is transpiled for browser compatibility
3. **Asset Copying**: Static files (manifest, styles, icons) are copied to `dist/`
4. **Package Creation**: Extension is packaged into a zip file for distribution

## Loading the Extension

1. Run the build: `./build.sh`
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `dist/` directory

## Key Improvements Over Legacy Version

### 1. Code Organization
- **Before**: Single monolithic `content.js` file
- **After**: Modular components with clear responsibilities

### 2. Maintainability
- **Before**: Difficult to locate and modify specific functionality
- **After**: Each feature is in its own module with clear interfaces

### 3. Testing
- **Before**: No testing framework
- **After**: Jest testing setup with component-specific tests

### 4. Build Process
- **Before**: Manual file management
- **After**: Automated webpack bundling with optimization

### 5. Development Experience
- **Before**: Edit and reload manually
- **After**: Hot reloading with `npm run dev`

## Extension Features

### Date Grouping
Automatically groups emails by date categories:
- Today
- Yesterday
- Last 7 days
- Last 30 days
- Older

### Modern Gmail Interface
- Clean, modern styling
- Improved visual hierarchy
- Enhanced readability

### Smart Observers
- Efficient DOM change detection
- Debounced updates to prevent performance issues
- Retry logic for Gmail loading

## Configuration

### Webpack (`webpack.config.js`)
- Entry point: `./src/content.js`
- Output: `./dist/content.js`
- Babel loader for ES6+ transformation
- Source maps for debugging

### Babel (`.babelrc`)
- ES6+ to ES5 transformation
- Module compatibility

### Package Scripts
- `build`: Production build
- `dev`: Development mode with watching
- `test`: Run Jest tests

## Troubleshooting

### Build Issues
1. Ensure all dependencies are installed: `npm install`
2. Check for syntax errors in source files
3. Verify webpack configuration

### Extension Loading Issues
1. Ensure manifest.json is valid
2. Check that all referenced files exist in dist/
3. Verify Chrome extension permissions

### Runtime Issues
1. Check browser console for errors
2. Verify Gmail page structure hasn't changed
3. Test with different Gmail views (inbox, sent, etc.)

## Future Enhancements

1. **Additional Bundling Strategies**: Group by sender, importance, etc.
2. **User Preferences**: Customizable grouping options
3. **Performance Monitoring**: Bundle performance metrics
4. **Advanced Testing**: Integration and e2e tests
5. **Hot Module Replacement**: Faster development iteration

## Contributing

1. Follow the modular architecture patterns
2. Add tests for new components
3. Update documentation for new features
4. Use the provided build system for consistency