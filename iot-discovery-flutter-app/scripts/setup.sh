#!/bin/bash

# IoT Discovery Flutter App Setup Script
# This script sets up the development environment and runs the app

echo "🚀 Setting up IoT Discovery Flutter App..."

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    echo "❌ Flutter is not installed. Please install Flutter first."
    echo "Visit: https://docs.flutter.dev/get-started/install"
    exit 1
fi

echo "✅ Flutter is installed"

# Check Flutter doctor
echo "🔍 Running Flutter doctor..."
flutter doctor

# Get dependencies
echo "📦 Getting Flutter dependencies..."
flutter pub get

# Generate code (JSON serialization)
echo "🔧 Generating code..."
flutter packages pub run build_runner build --delete-conflicting-outputs

# Check for any issues
echo "🔍 Running flutter analyze..."
flutter analyze

# Run tests
echo "🧪 Running tests..."
flutter test

echo "✅ Setup complete!"
echo ""
echo "🎮 To run the app:"
echo "  flutter run"
echo ""
echo "🧪 To run tests:"
echo "  flutter test                    # Unit & Widget tests"
echo "  flutter test integration_test/  # Integration tests"
echo ""
echo "🔧 To generate code:"
echo "  flutter packages pub run build_runner build --delete-conflicting-outputs"
echo ""
echo "📱 Enjoy the gamified onboarding experience!"
