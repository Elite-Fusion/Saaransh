# CLAUDE.md

# Saaransh AI

## Project Overview

Saaransh is an AI-powered Crime Investigation Assistant developed for the Karnataka State Police Datathon.

The system enables police officers to interact with crime data using natural language (English and Kannada), perform crime analysis, detect similar cases, visualize criminal networks, predict crime hotspots, and provide explainable AI responses.

The project must prioritize accuracy, explainability, maintainability, modularity, and security.

---

# Technology Stack

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router

## Backend

- FastAPI
- Python 3.12+
- SQLAlchemy
- Pydantic

## Database

- PostgreSQL
- Supabase
- pgvector

## AI

Primary Provider:
- Google Gemini API (Free Tier)

Prompt Management:
- Markdown Prompt Files

Embeddings:
- Sentence Transformers

## Graph Database

- Neo4j

## Machine Learning

- scikit-learn
- DBSCAN
- Prophet

## Deployment

Frontend
- Vercel

Backend
- Railway or Render

---

# Project Goals

The application should support:

- Natural Language → SQL
- Crime analytics
- Similar case detection
- Cross-case linking
- Crime hotspot prediction
- Criminal relationship graph
- Voice search
- Explainable AI
- Audit logging
- Role-based access

---

# Development Principles

Always build production-quality code.

Write modular code.

Keep every module independent.

Avoid unnecessary complexity.

Never generate temporary or hacky implementations.

Always prefer readability over clever code.

---

# Coding Standards

Always use:

- Type hints
- Pydantic models
- SQLAlchemy ORM
- Environment variables
- Dependency Injection where appropriate

Never write duplicated code.

Keep functions short.

Split business logic into service classes.

Never place business logic inside API routes.

---

# Folder Organization

Backend should contain:

backend/

- api/
- models/
- schemas/
- services/
- database/
- middleware/
- utils/
- config/
- ai/

Frontend should contain:

frontend/

- components/
- pages/
- hooks/
- services/
- contexts/
- layouts/
- assets/

---

# AI Development Rules

Primary AI Provider

Google Gemini API

Important Rules

Never hardcode Gemini throughout the project.

Always use an abstraction layer.

Application

↓

AI Service

↓

Provider

↓

Gemini API

If we change providers later, only the provider layer should change.

Future providers may include

- Claude
- OpenAI
- Groq
- OpenRouter

---

# Prompt Management

Never hardcode prompts inside Python files.

Store prompts inside

prompts/

Example

prompts/

- system_prompt.md
- sql_prompt.md
- explanation_prompt.md
- similarity_prompt.md

Load prompts dynamically.

---

# SQL Generation Rules

Natural language must generate SQL safely.

Allowed

- SELECT

Forbidden

- DELETE
- UPDATE
- INSERT
- DROP
- ALTER
- TRUNCATE

Always validate generated SQL before execution.

Never trust LLM-generated SQL without validation.

---

# Database Rules

Never guess table names.

Never guess column names.

Always use the provided SQL schema.

Always maintain foreign-key relationships.

Optimize joins whenever possible.

Avoid SELECT *.

Always fetch only required columns.

---

# API Standards

Each endpoint must have

- Request Model
- Response Model
- Error Handling
- Validation
- Logging

Return consistent JSON responses.

---

# Error Handling

Never hide exceptions.

Return meaningful errors.

Log unexpected exceptions.

Avoid generic Exception blocks.

---

# Logging

Every AI request should log

- Timestamp
- User
- Prompt
- Generated SQL
- Execution Time
- Success/Failure

Never log API keys.

---

# Security Rules

Store secrets only in .env

Never hardcode

- API Keys
- Database Passwords
- Tokens

Always sanitize user input.

Prevent SQL Injection.

Validate every request.

---

# Explainability

Every AI answer should include

- Why this answer was generated
- Which records were used
- Confidence level
- Supporting evidence

Never fabricate evidence.

---

# Performance

Prefer pagination.

Cache repeated lookups where appropriate.

Optimize expensive joins.

Avoid N+1 queries.

---

# Development Workflow

For every task:

1. Explain the implementation plan.
2. Mention files to be created.
3. Mention files to be modified.
4. Generate complete code.
5. Explain how to test it.
6. Wait for approval before continuing.

Never jump to the next feature automatically.

---

# Architecture

React Frontend

↓

FastAPI Backend

↓

Service Layer

↓

AI Service

↓

Gemini Provider

↓

Google Gemini API

↓

PostgreSQL + Supabase

↓

Neo4j

↓

Machine Learning

---

# Documentation

Whenever creating a new module:

Generate

- README
- Comments
- Docstrings

Explain folder purpose.

Explain API usage.

---

# Code Quality

Write code suitable for production.

Follow clean architecture.

Keep modules reusable.

Keep code maintainable.

Avoid unnecessary dependencies.

Never leave TODOs unless explicitly requested.

---

# Important Instructions

Before generating any code:

1. Read the project documentation.
2. Read the SQL schema.
3. Understand table relationships.
4. Explain the implementation plan.
5. Generate production-ready code only.

Never assume database schema.

Never invent table names.

Never invent columns.

Always ask if additional clarification is needed before implementing complex features.