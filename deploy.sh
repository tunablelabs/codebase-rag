#!/bin/bash
set -x
chmod +x /home/ec2-user/codebase-rag/frontend/deploy.sh

echo "Starting deployment..."
cd /home/ec2-user/codebase-rag
# Pull latest changes
git pull origin main
cd /home/ec2-user/codebase-rag/frontend
# Install dependencies
npm install

# Build the Next.js app
npm run build

# Restart the application
pm2 restart frontend || pm2 start npm --name "frontend" -- start

# Save PM2 process
pm2 save
echo "Deployment complete!"
