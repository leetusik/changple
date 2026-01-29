# Changple AI - v3.0.0 (Monorepo MSA)

## Overview

This document outlines the target architecture for restructuring Changple AI from a Django monolith to a Microservices Architecture (MSA) managed as a monorepo.

---

## Project Root Structure

```
changple/
├── docker-compose.yml              # Main orchestration (dev)
├── docker-compose.prod.yml         # Production orchestration
├── docker-compose.override.yml     # Local dev overrides
├── .env.example                    # Environment template
├── .gitignore
├── README.md
├── Makefile                        # Common commands
│
├── nginx/                          # Main reverse proxy
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── conf.d/
│   │   ├── default.conf
│   │   ├── upstream.conf
│   │   └── ssl.conf
│   └── certs/                      # SSL certificates (gitignored)
│
├── services/
│   ├── core/                       # Django WAS (users, content, auth)
│   ├── client/                     # React frontend
│   ├── agent/                      # LangGraph AI agent (FastAPI)
│   └── scraper/                    # Web scraper service (FastAPI, optional)
│
├── infra/                          # Infrastructure configs
│   ├── postgres/
│   │   └── init.sql
│   ├── redis/
│   │   └── redis.conf
│   └── scripts/
│       ├── deploy.sh
│       └── backup.sh
│
└── docs/                           # Documentation
    ├── architecture.md
    ├── api-spec.md
    └── deployment.md
```

