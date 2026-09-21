# SafeSec Implementation Plan

## Phase 1: Camera and detection foundation

- [x] Bootstrap Python packaging with `pyproject.toml` and uv dependency groups
- [x] Add root project documentation and repository plan
- [x] Define validated camera configuration and frame contracts
- [x] Implement injectable OpenCV capture with cleanup and bounded failures
- [x] Define vendor-neutral detection and bounding-box contracts
- [x] Add lazy Ultralytics inference adapter
- [x] Add deterministic IoU tracking with stable IDs and expiry
- [x] Add hardware-free camera, inference, tracking, and pipeline tests
- [x] Add a local capture/detection CLI
- [x] Add video-file replay through the same pipeline
- [x] Add security label allow-list for person/dog/cat detection
- [x] Run the 507-frame `samples/frontdoor_30fps.mp4` replay successfully
- [ ] Complete a Windows webcam smoke test
- [x] Measure basic video replay throughput and tracking continuity

## Phase 2: Local recording

- [x] Define encoded segment and metadata contracts
- [x] Implement segment rotation and interrupted-write recovery
- [x] Implement retention policies and metadata-to-segment linkage
- [x] Define and implement encryption boundaries
- [x] Add recording, retention, and recovery tests
- [x] Wire local MP4 recording into the self-hosted CLI

## Phase 3: Alerts

- [x] Define track-start and track-end event contracts
- [x] Add person, zone, and confidence rules
- [x] Add deduplication and cooldown handling
- [x] Add schedule rules and notification retry behavior
- [x] Add alert rule and delivery tests

## Phase 4: Device API and local authentication

- [x] Define device identity and authenticated local API
- [x] Add authorization and credential revocation
- [x] Add authenticated dashboard HTTP access
- [x] Add audit logging, rate limiting, and key rotation
- [x] Add durable audit storage and offline/reconnect behavior
- [x] Add security and integration tests

## Phase 5: Applications and hardware operations

- [x] Define web dashboard and mobile notification read models
- [x] Build local operational web view, live MJPEG feed, event history, and review snapshots
- [ ] Add authenticated remote-view workflows if remote access becomes a product requirement
- [x] Add Docker development packaging
- [x] Add self-hosted dashboard, recording, and model volumes to Docker Compose
- [x] Document provisioning and update requirements
- [ ] Implement signed updates, rollback, observability, and hardware-specific drivers

## Working rules

1. Add focused tests before wiring each phase into the end-to-end pipeline.
2. Keep camera, inference, storage, and transport implementations behind stable contracts.
3. Keep local operation functional without remote access or cloud services.
4. Keep model weights, recordings, credentials, and device secrets out of version control.
5. Review open-source license compatibility before selecting production models and runtimes.
