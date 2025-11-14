# Project Brief: AI Video Generation Pipeline

## Overview
An end-to-end AI video generation pipeline that transforms text prompts into professional 30-second advertisement videos for a $5,000 bounty competition.

**Version**: 2.0  
**Team**: 3-person team with phase-based vertical slices  
**Region**: AWS us-east-2 (Ohio)

## Core Objective
Build a production-ready system that generates high-quality 30s ad videos from natural language prompts, using a hybrid approach: deterministic templates for structure + generative AI for content.

## Timeline
- **Total Duration**: 7 days
- **MVP Target**: 48 hours (Day 1-2)
- **Final Submission**: Day 7

## Key Innovation
Six-phase pipeline that progressively refines from low-fidelity animatics to high-quality final videos, using animatics as motion references to ensure temporal consistency.

## Success Criteria

### Competition Judging (100%)
1. **Output Quality (40%)**: Visual coherence, A/V sync, creative execution
2. **Pipeline Architecture (25%)**: Code quality, system design, error handling
3. **Cost Effectiveness (20%)**: <$2/minute generation cost
4. **User Experience (15%)**: Ease of use, feedback quality

### Technical Requirements
- 1080p resolution, 30 FPS
- Generation time: <10 minutes for 30s video
- 90%+ successful generation rate
- Support 1 concurrent video per user (MVP)

## Scope

### MVP (48 hours)
- Generate 30-second ad videos from text prompts
- Support 3 ad templates (product showcase, lifestyle, announcement)
- Consistent visual style across all clips
- Audio-visual synchronization with generated background music
- Deploy to AWS with working web interface

### Final Submission (7 days)
- User authentication and project persistence
- Reference asset library with vector database
- Iterative refinement capabilities
- Timeline editing interface
- Multi-format export

## Budget
- **Infrastructure**: ~$100/month (~$25 for competition week)
- **API Costs**: $200-$250 for development + showcase
- **Total Competition Week**: ~$225-$275
- **Per Video Cost**: $1.76 (dev) or $3.26 (final)

## Team Structure (3 People)
- **Person A**: Phase 1 (Validation) + Phase 2 (Animatic) + Generate Form
- **Person B**: Phase 3 (References) + Phase 4 (Chunks) + Progress Indicator
- **Person C**: Phase 5 (Refinement) + Phase 6 (Export) + Video Player

**Philosophy**: Phase-based vertical slices minimize merge conflicts and enable parallel development.

## Deliverables
1. Working end-to-end pipeline (6 phases)
2. Web interface (React + Tailwind + shadcn/ui)
3. REST API (FastAPI + Celery)
4. 10+ showcase videos
5. Architecture diagrams (Mermaid)
6. Technical documentation
7. Demo video (5-7 minutes)
8. GitHub repository
9. Deployed production URL (us-east-2)

