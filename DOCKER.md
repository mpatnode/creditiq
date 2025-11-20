# Docker Deployment Guide

## Quick Start

### Option 1: Using Make (Recommended)
```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your credentials and set BOX_CONFIG_PATH

# 2. Build, start, and initialize everything
make docker-init

# 3. View logs
make docker-logs
```

### Option 2: Manual Setup
1. **Set up environment variables and Box config**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   
   # Place your Box JWT config file as .box_config.json in the project root
   cp /path/to/your/box_jwt_config.json .box_config.json
   ```

2. **Build and start services**
   ```bash
   docker-compose up -d
   ```

3. **Initialize database**
   ```bash
   # Wait for services to be healthy
   docker-compose ps
   
   # Initialize database tables
   docker-compose exec app python scripts/init_db.py
   ```

4. **Check service status**
   ```bash
   docker-compose ps
   ```

5. **View logs**
   ```bash
   docker-compose logs -f app
   ```

### Access the Application
- Web UI: http://localhost:8080
- API Docs: http://localhost:8080/api/docs
- MCP Server: http://localhost:8005

## Services

- **app**: Flask application (port 8080)
- **postgres**: PostgreSQL database (port 5432)
- **box-mcp**: Box MCP server (Python implementation) with SSE transport (port 8005)

## Useful Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### Rebuild after code changes
```bash
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build app
docker-compose up -d --build box-mcp
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
```

### Execute commands in container
```bash
# Access app shell
docker-compose exec app bash

# Run database migrations
docker-compose exec app python -m alembic upgrade head

# Run tests
docker-compose exec app pytest
```

### Database operations
```bash
# Initialize/reset database tables
docker-compose exec app python scripts/init_db.py

# Access PostgreSQL
docker-compose exec postgres psql -U credit_rating_user -d credit_rating_db

# Check tables
docker-compose exec postgres psql -U credit_rating_user -d credit_rating_db -c "\dt"

# Backup database
docker-compose exec postgres pg_dump -U credit_rating_user credit_rating_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U credit_rating_user credit_rating_db < backup.sql
```

## Architecture

The application uses a microservices architecture:

- **Flask App** connects to **Box MCP Server** via HTTP/SSE at `http://box-mcp:8005/sse`
- **Box MCP Server** is built from the Python implementation at [box-community/mcp-server-box](https://github.com/box-community/mcp-server-box)
- All services communicate over a private Docker network

## Production Considerations

1. **Environment Variables**: Set strong passwords and secrets in `.env`
2. **Volumes**: Database data persists in `postgres_data` volume
3. **Networking**: Services communicate via `credit_rating_network`
4. **Health Checks**: All services have health checks configured
5. **Restart Policy**: Services restart automatically unless stopped manually
6. **Box Config**: Ensure your Box JWT config file is properly mounted

## Troubleshooting

### App won't start
```bash
# Check logs
docker-compose logs app

# Verify database is ready
docker-compose exec postgres pg_isready -U credit_rating_user

# Check MCP server
docker-compose logs box-mcp
```

### MCP Connection Issues
```bash
# Check if MCP server is healthy
docker-compose ps box-mcp

# Test MCP server endpoint
curl http://localhost:8005/health

# View MCP server logs
docker-compose logs -f box-mcp
```

### Database connection issues
- Ensure `DATABASE_URL` in `.env` matches postgres credentials
- Check if postgres service is healthy: `docker-compose ps`

### Port conflicts
If ports 8080, 8005, or 5432 are already in use, modify `docker-compose.yml`:
```yaml
ports:
  - "9000:5000"  # Use port 9000 instead of 8080
  - "9005:8005"  # Use port 9005 instead of 8005
```

### Box Configuration Issues
- Ensure `BOX_CONFIG_PATH` points to a valid Box JWT config file
- Verify the config file has correct permissions (readable)
- Check Box credentials are valid and not expired


## Quick Reference

### Common Make Commands
```bash
make docker-init      # Build, start, and initialize database
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-build     # Rebuild and restart services
make docker-logs      # View logs from all services
make db-init          # Initialize database (local development)
```

### Common Docker Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild services
docker-compose up -d --build

# View logs
docker-compose logs -f [service_name]

# Check service status
docker-compose ps

# Execute command in container
docker-compose exec app [command]

# Initialize database
docker-compose exec app python scripts/init_db.py
```

### Service URLs
- **Flask App**: http://localhost:8080
- **API Documentation**: http://localhost:8080/api/docs
- **Box MCP Server**: http://localhost:8005
- **PostgreSQL**: localhost:5432

### Environment Variables
Key variables to set in `.env`:
- `SECRET_KEY`: Flask secret key (change in production)
- `SEC_USER_AGENT`: Your contact email for SEC API
- `BOX_METHODOLOGY_FOLDER_ID`: Box folder ID for methodology
- `BOX_RATINGS_FOLDER_ID`: Box folder ID for ratings
- `BOX_TEMP_FOLDER_ID`: Box folder ID for temporary files
- `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, `BOX_ENTERPRISE_ID`: Box JWT credentials

### Box Configuration
Place your Box JWT config file as `.box_config.json` in the project root. This file will be mounted into the MCP server container.
