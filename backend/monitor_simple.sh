#!/bin/bash
# Simple monitoring - just follow logs
docker-compose logs -f --tail=100 api worker
