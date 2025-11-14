# Active Context

## Current Status
**Project Phase**: Initialization  
**PRD Version**: 2.0  
**Date**: November 14, 2025  
**Day**: 0 (Pre-Development)  
**Team Size**: 3 people  
**Region**: AWS us-east-2 (Ohio)

## What Just Happened
1. ✅ Created project repository
2. ✅ Comprehensive PRD v2.0 documented (1,954 lines)
3. ✅ Architecture diagrams added (Mermaid):
   - `architecture-deployment.mermaid` (82 lines) - AWS infrastructure
   - `architecture-pipeline.mermaid` (118 lines) - Six-phase workflow
4. ✅ Memory bank initialized with all core files
5. ✅ Git repository initialized and pushed to GitHub
6. ✅ Pulled latest changes from remote
7. 🔄 Updating memory bank with PRD v2.0 changes

## Current Focus
**Setting up project foundation and git repository**

### Immediate Tasks
1. Complete git initialization and push to GitHub
2. Create project directory structure
3. Set up Docker Compose environment
4. Initialize backend skeleton (FastAPI + Celery)
5. Initialize frontend skeleton (React + Vite)

## Recent Decisions

### Architectural Decisions (PRD v2.0)
1. **3-Person Team Structure**: Phase-based vertical slices
   - Person A: Phase 1 (Validation) + Phase 2 (Animatic) + Generate Form
   - Person B: Phase 3 (References) + Phase 4 (Chunks) + Progress Indicator
   - Person C: Phase 5 (Refinement) + Phase 6 (Export) + Video Player
   - Why: Zero merge conflicts, parallel development, clear ownership

2. **AWS Region**: us-east-2 (Ohio)
   - Why: Cost-effective, low latency, good availability
   
3. **Hybrid Approach**: Template-driven structure + AI content generation
   - Why: Reliability (90%+ success rate) + Creativity
   
4. **Six-Phase Pipeline**: Progressive refinement pattern
   - Phase 1: Validation (GPT-4)
   - Phase 2: Animatic (SDXL, internal reference)
   - Phase 3: References (SDXL)
   - Phase 4: Chunks (Zeroscope/AnimateDiff, parallel)
   - Phase 5: Refinement (FFmpeg + MusicGen)
   - Phase 6: Export (S3)

5. **AWS Elastic Beanstalk**: Over ECS or Lambda
   - Why: Simpler deployment, auto-scaling, managed load balancer
   - Cost: ~$87/month (~$25 for competition week)
   - Region: us-east-2 for all services

6. **Celery + Redis**: For job queue and workers
   - Why: Proven, scales well, supports parallel tasks
   - Pattern: Group execution for 15 video chunks

7. **Development vs Final Models**:
   - Dev: Zeroscope ($0.10/chunk) - Fast iteration
   - Final: AnimateDiff ($0.20/chunk) - High quality
   - Saves ~$150 during development

8. **Visual Documentation**: Added Mermaid diagrams
   - Deployment architecture (CloudFront → ALB → EB → S3/RDS/ElastiCache)
   - Pipeline workflow (6 phases with inputs/outputs)

### Template Strategy
Start with 3 templates:
1. **Product Showcase**: Luxury goods, details-focused
2. **Lifestyle Ad**: Real-world usage, dynamic
3. **Announcement**: Brand messaging, bold graphics

## Next Steps

### Immediate (Today)
1. ✅ Initialize git repository
2. ✅ Create memory bank (v1)
3. ✅ Push to GitHub
4. ✅ Pull updated PRD v2.0 and diagrams
5. 🔄 Update memory bank (v2 with team structure)
6. 🔲 Create directory structure (phase-based folders)
7. 🔲 Set up Docker Compose
8. 🔲 Create .env.example file

### Day 1 Morning (All Together - 2 hours)
**Shared Foundation** - Zero conflicts if done together first
- ✅ Review PRD v2.0 and architecture
- 🔲 Write `common/schemas.py` (PhaseInput/Output contracts)
- 🔲 Write `common/models.py` (VideoGeneration database model)
- 🔲 Write `orchestrator/pipeline.py` skeleton
- 🔲 Set up shared `services/` (API client interfaces)
- 🔲 Agree on Git workflow (feature branches, PR review)
- 🔲 Set up Docker Compose
- 🔲 Test: Can everyone run `docker-compose up` successfully?

### Day 1 Afternoon (Parallel - 6 hours)
**Person A** (Phases 1+2):
- Phase 1: Prompt validation (OpenAI integration, templates)
- Phase 2: Animatic generation (SDXL, S3 uploads)

**Person B** (Phases 3+4):
- Phase 3: Reference assets (style guide generation)
- Phase 4: Chunk generation (parallel execution, stitching)

**Person C** (Phases 5+6):
- Phase 5: Refinement (FFmpeg, MusicGen)
- Phase 6: Export (S3 upload, cleanup)

### Day 1-2 (MVP - 48 hours)
**Complete all 6 pipeline phases**
1. Phase 1: Prompt validation (GPT-4)
2. Phase 2: Animatic generation (SDXL)
3. Phase 3: Reference assets (SDXL)
4. Phase 4: Chunked video generation (Zeroscope)
5. Phase 5: Refinement (FFmpeg + MusicGen)
6. Phase 6: S3 upload + download

**End-to-End Testing**
- Generate first complete video
- Verify quality, timing, A/V sync
- Measure cost and generation time

## Active Considerations

### Cost Management
- Budget: $225-$275 for competition week
- Track costs per phase in database
- Use Zeroscope for all development
- Switch to AnimateDiff only for final 10 showcase videos

### Quality vs Speed Tradeoffs
- MVP: Prioritize speed (get working pipeline)
- Polish phase: Prioritize quality (fine-tune prompts, color grading)
- Decision point: Day 3 (after MVP complete)

### Risk Areas to Watch
1. **Temporal Consistency**: Will animatic-as-reference work?
   - Mitigation: Test early (Day 1)
   - Fallback: Motion-first pipeline (documented in PRD)

2. **API Rate Limits**: Replicate limits 50 concurrent predictions
   - Mitigation: Throttle to 15 chunks at a time
   - Monitor: Check rate limit headers in responses

3. **Generation Time**: Target <10 minutes
   - Current estimate: 7-8 minutes
   - If exceeds: Reduce chunk count or chunk duration

## Questions to Resolve

### Before Day 1
- ❓ AWS account ready? (Need to verify credentials)
- ❓ Replicate API token obtained?
- ❓ OpenAI API key obtained?

### During MVP Development
- ❓ Which template to test first? (Recommend: product_showcase)
- ❓ What's the optimal chunk overlap? (Start with 0.5s)
- ❓ Should we generate all 15 chunks or start with 5 for testing?

### Before Final Submission
- ❓ Which 10 videos to showcase with AnimateDiff?
- ❓ How to structure demo video?
- ❓ What documentation needs to be written?

## Current Blockers
**None** - Ready to proceed with development

## Success Indicators (To Track)
- [ ] Local Docker Compose working
- [ ] First successful prompt validation (Phase 1)
- [ ] First animatic generated (Phase 2)
- [ ] First video chunk generated (Phase 4)
- [ ] First complete 30s video
- [ ] Deploy to AWS (Web + Worker tiers)
- [ ] First video generated in production
- [ ] Generate 10 showcase videos
- [ ] Complete documentation
- [ ] Submit to competition

## Notes
- PRD is comprehensive and detailed (1,716 lines)
- All 6 phases are well-specified
- Cost breakdown is clear ($1.76-$3.26 per video)
- Architecture is proven (similar to existing systems)
- Timeline is aggressive but achievable (MVP in 48 hours)

