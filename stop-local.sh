#!/bin/bash
echo "Stopping local environment for PymAI..."
pm2 stop ecosystem.config.js
pm2 delete ecosystem.config.js
