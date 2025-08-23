@echo off
REM IoT Discovery Flutter App Setup Script for Windows
REM This script sets up the development environment and runs the app

echo 🚀 Setting up IoT Discovery Flutter App...

REM Check if Flutter is installed
flutter --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Flutter is not installed. Please install Flutter first.
    echo Visit: https://docs.flutter.dev/get-started/install
    pause
    exit /b 1
)

echo ✅ Flutter is installed

REM Check Flutter doctor
echo 🔍 Running Flutter doctor...
flutter doctor

REM Get dependencies
echo 📦 Getting Flutter dependencies...
flutter pub get

REM Generate code (JSON serialization)
echo 🔧 Generating code...
flutter packages pub run build_runner build --delete-conflicting-outputs

REM Check for any issues
echo 🔍 Running flutter analyze...
flutter analyze

REM Run tests
echo 🧪 Running tests...
flutter test

echo ✅ Setup complete!
echo.
echo 🎮 To run the app:
echo   flutter run
echo.
echo 🧪 To run tests:
echo   flutter test                    # Unit ^& Widget tests
echo   flutter test integration_test/  # Integration tests
echo.
echo 🔧 To generate code:
echo   flutter packages pub run build_runner build --delete-conflicting-outputs
echo.
echo 📱 Enjoy the gamified onboarding experience!
pause
