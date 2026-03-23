#!/bin/bash
# Setup logging directory and permissions

echo "🔧 Setting up logging directory..."

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    mkdir -p logs
    echo "✅ Created logs/ directory"
else
    echo "ℹ️  logs/ directory already exists"
fi

# Create .gitignore for logs
if [ ! -f "logs/.gitignore" ]; then
    echo "*.log" > logs/.gitignore
    echo "*.log.*" >> logs/.gitignore
    echo "!*.gitignore" >> logs/.gitignore
    echo "✅ Created logs/.gitignore"
else
    echo "ℹ️  logs/.gitignore already exists"
fi

echo ""
echo "📝 Logging setup complete!"
echo "Logs will be stored in: $(pwd)/logs/"
echo ""
echo "To view logs in real-time:"
echo "  tail -f logs/qr_login.log"
echo ""
