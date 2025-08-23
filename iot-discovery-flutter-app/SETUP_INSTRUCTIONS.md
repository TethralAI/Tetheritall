# IoT Discovery Flutter App - Setup Instructions

## Prerequisites

### 1. Flutter SDK Installation

#### Windows
1. Download Flutter SDK from [flutter.dev](https://flutter.dev/docs/get-started/install/windows)
2. Extract to `C:\flutter` (or your preferred location)
3. Add Flutter to PATH:
   - Open System Properties → Environment Variables
   - Add `C:\flutter\bin` to Path variable
4. Verify installation:
   ```bash
   flutter doctor
   ```

#### macOS
1. Download Flutter SDK from [flutter.dev](https://flutter.dev/docs/get-started/install/macos)
2. Extract to your home directory
3. Add to PATH in `~/.zshrc` or `~/.bash_profile`:
   ```bash
   export PATH="$PATH:`pwd`/flutter/bin"
   ```
4. Verify installation:
   ```bash
   flutter doctor
   ```

#### Linux
1. Download Flutter SDK from [flutter.dev](https://flutter.dev/docs/get-started/install/linux)
2. Extract to your home directory
3. Add to PATH in `~/.bashrc`:
   ```bash
   export PATH="$PATH:`pwd`/flutter/bin"
   ```
4. Verify installation:
   ```bash
   flutter doctor
   ```

### 2. Android Studio / Xcode

#### Android Development
1. Install [Android Studio](https://developer.android.com/studio)
2. Install Android SDK
3. Create Android Virtual Device (AVD) for testing
4. Accept Android licenses:
   ```bash
   flutter doctor --android-licenses
   ```

#### iOS Development (macOS only)
1. Install [Xcode](https://developer.apple.com/xcode/)
2. Install iOS Simulator
3. Accept Xcode licenses:
   ```bash
   sudo xcodebuild -license accept
   ```

### 3. IDE Setup

#### VS Code (Recommended)
1. Install [VS Code](https://code.visualstudio.com/)
2. Install Flutter extension
3. Install Dart extension
4. Install additional extensions:
   - Flutter Widget Snippets
   - Awesome Flutter Snippets
   - Flutter Tree

#### Android Studio
1. Install Flutter plugin
2. Install Dart plugin
3. Restart IDE

## Project Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd iot-discovery-flutter-app
```

### 2. Install Dependencies
```bash
flutter pub get
```

### 3. Generate Code
```bash
flutter packages pub run build_runner build --delete-conflicting-outputs
```

### 4. Setup Environment Variables
1. Copy `.env.example` to `.env`
2. Configure your environment variables:
   ```env
   # Firebase Configuration
   FIREBASE_API_KEY=your_firebase_api_key
   FIREBASE_APP_ID=your_firebase_app_id
   FIREBASE_MESSAGING_SENDER_ID=your_sender_id
   FIREBASE_PROJECT_ID=your_project_id
   
   # Backend API
   API_BASE_URL=http://localhost:8000
   
   # Analytics
   ANALYTICS_ENABLED=true
   
   # Debug Mode
   DEBUG_MODE=true
   ```

### 5. Firebase Setup

#### Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create new project
3. Enable services:
   - Authentication
   - Cloud Firestore
   - Cloud Functions
   - Analytics
   - Crashlytics
   - Performance Monitoring
   - Cloud Messaging

#### Configure Firebase for Flutter
1. Add Android app:
   - Package name: `com.tetheritall.iot_discovery_app`
   - Download `google-services.json`
   - Place in `android/app/`

2. Add iOS app:
   - Bundle ID: `com.tetheritall.iotDiscoveryApp`
   - Download `GoogleService-Info.plist`
   - Place in `ios/Runner/`

3. Update `android/app/build.gradle`:
   ```gradle
   apply plugin: 'com.google.gms.google-services'
   ```

4. Update `ios/Runner/Info.plist`:
   ```xml
   <key>CFBundleURLTypes</key>
   <array>
     <dict>
       <key>CFBundleURLName</key>
       <string>REVERSED_CLIENT_ID</string>
       <key>CFBundleURLSchemes</key>
       <array>
         <string>YOUR_REVERSED_CLIENT_ID</string>
       </array>
     </dict>
   </array>
   ```

### 6. Backend Setup

#### Start Backend Services
1. Navigate to backend directory:
   ```bash
   cd ../services
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start backend server:
   ```bash
   python -m api.server
   ```

#### Database Setup
1. Install PostgreSQL
2. Create database:
   ```sql
   CREATE DATABASE iot_discovery;
   ```

3. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Running the App

### 1. Development Mode
```bash
flutter run
```

### 2. Debug Mode
```bash
flutter run --debug
```

### 3. Release Mode
```bash
flutter run --release
```

### 4. Profile Mode
```bash
flutter run --profile
```

## Testing

### 1. Unit Tests
```bash
flutter test
```

### 2. Widget Tests
```bash
flutter test test/features/onboarding/widgets/
```

### 3. Integration Tests
```bash
flutter test integration_test/
```

### 4. Test Coverage
```bash
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
```

## Building for Production

### 1. Android APK
```bash
flutter build apk --release
```

### 2. Android App Bundle
```bash
flutter build appbundle --release
```

### 3. iOS Archive
```bash
flutter build ios --release
```

### 4. Web Build
```bash
flutter build web --release
```

## Troubleshooting

### Common Issues

#### 1. Flutter Doctor Issues
```bash
flutter doctor -v
```
Follow the recommendations to fix any issues.

#### 2. Dependency Issues
```bash
flutter clean
flutter pub get
flutter packages pub run build_runner build --delete-conflicting-outputs
```

#### 3. Android Build Issues
```bash
cd android
./gradlew clean
cd ..
flutter clean
flutter pub get
```

#### 4. iOS Build Issues
```bash
cd ios
pod deintegrate
pod install
cd ..
flutter clean
flutter pub get
```

#### 5. Firebase Issues
1. Verify `google-services.json` is in correct location
2. Check Firebase project configuration
3. Ensure all required Firebase services are enabled

#### 6. Backend Connection Issues
1. Verify backend server is running
2. Check API_BASE_URL in `.env`
3. Test API endpoints manually

### Performance Optimization

#### 1. Enable R8/ProGuard (Android)
Update `android/app/build.gradle`:
```gradle
android {
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
        }
    }
}
```

#### 2. Enable Bitcode (iOS)
Update `ios/Podfile`:
```ruby
post_install do |installer|
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['ENABLE_BITCODE'] = 'YES'
    end
  end
end
```

## Development Workflow

### 1. Feature Development
1. Create feature branch:
   ```bash
   git checkout -b feature/onboarding-enhancement
   ```

2. Make changes and test:
   ```bash
   flutter test
   flutter run
   ```

3. Commit changes:
   ```bash
   git add .
   git commit -m "Add onboarding enhancement"
   ```

4. Push and create PR:
   ```bash
   git push origin feature/onboarding-enhancement
   ```

### 2. Code Generation
After modifying models or services:
```bash
flutter packages pub run build_runner build --delete-conflicting-outputs
```

### 3. Testing Strategy
1. Write unit tests for business logic
2. Write widget tests for UI components
3. Write integration tests for user flows
4. Run all tests before committing

### 4. Code Quality
1. Run linter:
   ```bash
   flutter analyze
   ```

2. Format code:
   ```bash
   flutter format .
   ```

3. Check for unused imports:
   ```bash
   flutter analyze --no-fatal-infos
   ```

## Deployment

### 1. Android Play Store
1. Build app bundle:
   ```bash
   flutter build appbundle --release
   ```

2. Upload to Google Play Console
3. Configure release notes and screenshots
4. Submit for review

### 2. iOS App Store
1. Build archive:
   ```bash
   flutter build ios --release
   ```

2. Open Xcode and archive
3. Upload to App Store Connect
4. Configure release information
5. Submit for review

### 3. Web Deployment
1. Build web version:
   ```bash
   flutter build web --release
   ```

2. Deploy to hosting service (Firebase Hosting, Netlify, etc.)

## Monitoring and Analytics

### 1. Firebase Analytics
- Track user engagement
- Monitor app performance
- Analyze user behavior

### 2. Crashlytics
- Monitor app crashes
- Track error rates
- Get crash reports

### 3. Performance Monitoring
- Monitor app startup time
- Track network requests
- Analyze UI performance

## Security Considerations

### 1. API Security
- Use HTTPS for all API calls
- Implement proper authentication
- Validate all inputs

### 2. Data Privacy
- Follow GDPR guidelines
- Implement data encryption
- Provide privacy controls

### 3. App Security
- Use secure storage for sensitive data
- Implement certificate pinning
- Regular security updates

## Support and Resources

### 1. Documentation
- [Flutter Documentation](https://flutter.dev/docs)
- [Dart Documentation](https://dart.dev/guides)
- [Firebase Documentation](https://firebase.google.com/docs)

### 2. Community
- [Flutter Community](https://flutter.dev/community)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/flutter)
- [Reddit r/FlutterDev](https://reddit.com/r/FlutterDev)

### 3. Tools
- [Flutter Inspector](https://flutter.dev/docs/development/tools/flutter-inspector)
- [Dart DevTools](https://dart.dev/tools/dart-devtools)
- [Flutter Performance](https://flutter.dev/docs/perf/ui-performance)

## Next Steps

1. **Complete Setup**: Follow all setup instructions above
2. **Run Tests**: Ensure all tests pass
3. **Start Development**: Begin implementing features
4. **Deploy**: Deploy to app stores when ready
5. **Monitor**: Set up monitoring and analytics
6. **Iterate**: Continuously improve based on user feedback

For additional support, please refer to the project documentation or contact the development team.
