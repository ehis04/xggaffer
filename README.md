# xgGaffer: Football Analytics and Coaching Platform

![Backend](https://img.shields.io/badge/backend-Django_REST_Framework-0C4B33)
![Frontend](https://img.shields.io/badge/frontend-React_TypeScript-3178C6)
![Database](https://img.shields.io/badge/database-PostgreSQL-336791)
![Machine Learning](https://img.shields.io/badge/ML-scikit--learn-F7931E)
![Status](https://img.shields.io/badge/status-final_year_project-purple)

**Project:** xgGaffer  
**Module:** CSC1097 Final Year Project  
**Institution:** Dublin City University  
**Authors:** Ehis Oghina, Elizabeth Adeniran
**Supervisor:** Dr. Ellen Rushe
**Academic Year:** 2025/2026

---

## Abstract

xgGaffer is a full-stack football analytics and coaching platform designed to bring the wider footballing community together through insights and understanding. The platform supports users with a variety of roles in the beautiful game. Whether users are fans, players, managers, referees, scouts or simple sporting enthusiasts, there are elements catered to their interests. On this platform coaches can manage clubs(both real and imaginary), players and fans can browse livefootball content, and scouts can view advanced metrics and gain deeper insight through data-driven predictive tools.
The system is built with Django REST Framework backend, React TypeScript frontend, PostgreSQL database, Redis/Celery background processing, and Python machine learning services trained on football match data.

xgGaffer demonstrates the ability to turn data into knowledge and connect communities while doing so.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [Machine Learning and Prediction Layer](#machine-learning-and-prediction-layer)
6. [Deterministic Interpretation Layer](#deterministic-interpretation-layer)
7. [Repository Structure](#repository-structure)
8. [Local Development Setup](#local-development-setup)
9. [Environment Variables](#environment-variables)
10. [Running the Application](#running-the-application)
11. [Testing](#testing)
12. [Deployment](#deployment)
13. [Project Documentation](#project-documentation)
14. [Known Limitations](#known-limitations)
15. [Future Work](#future-work)
16. [Contributors and Acknowledgements](#contributors-and-acknowledgements)
17. [Licence](#licence)

---

## Project Overview

xgGaffer was created to bridge the gap between advanced metrics and the benefits of understanding their impact on the game and wider communities who have limited accessibility to such information in a way that is easy to consume and understand. People from every facet of the game kind find use and enjoyment in connecting with their peers and improving their understanding of the seemingly simple they’ve become accustomed to.

xgGaffer brings together key points of interest that have remained fractured across the internet for the last number of years. Coaches can manage their squads, fans can engage with current footballing events, users can educate themselves about different areas, and analysts can further work.

The application is designed around four main stakeholder groups.

| Stakeholder       | Main Needs                                                          | iFoot Support                                                                                |
| ----------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Coaches           | Manage teams, squads, formations, fixtures and tactical preparation | Club management, player rosters, teamsheets, tactics, resources and calendar-style workflows |
| Referees          | Study Laws of the Game, track progress and practise decision-making | Referee learning modules, quizzes, progress tracking and referee dashboards                  |
| Players           | Maintain player profiles and participate in club/team workflows     | Player profiles, club membership, squad assignment and teamsheet involvement                 |
| Fans and Analysts | Explore football data, predictions and football content             | Live football pages, prediction widgets, articles, recommendations and community features    |

The goal of this project is to show both technical depth and practical usefulness. It combines a full-stack architecture with machine learning and football specific domain modelling.

```md
![xgGaffer platform overview](docs/documentation/images/readme/platform-overview.png)
```

---

## Key Features

### Authentication and User Management

- Email-based registration with verification flow (token-based callback).
- Password reset via email with secure token validation.
- Role selection at account creation: Coach, Player, Referee or Fan.
- Role-specific profile pages with different fields and functionality per role.
- Follow and follower relationships between users with automatic count tracking.
- User profiles with display name, bio, visibility settings and active role management.
- httpOnly cookie/JWT-style token authentication with CSRF protection.

### Coaching and Club Management

- Create and manage football clubs with public or private visibility.
- Club membership via shareable join codes or direct invitations with approval workflows.
- Join request management: accept, reject or withdraw pending requests.
- Role-based club permissions distinguishing club owners and members.
- Maintain squads linked to canonical player profiles or standalone custom entries.
- Track club player injuries with status and timeline.
- Upload and manage coaching resources and training files with view tracking.
- Manage club fixtures with scheduling and result recording.
- Import historical club data via provider-linked import jobs.
- Store manual player statistics alongside enriched provider data.

### Teamsheets and Formation Builder

- Build starting XIs and benches with a visual interactive pitch renderer.
- Select predefined formations (4-4-2, 4-3-3, 4-2-3-1, 3-5-2 and other supported shapes) and assign players to positions with pitch co-ordinates.
- Link teamsheet slots to club players or enter custom player names.
- Save teamsheets as reusable templates for recurring match types and quick preparation.

### Tactics Board

- Create a canvas-based tactics board for visual tactical planning.
- Add items to the canvas: player markers, ball, arrows, lines, zones and text annotations.
- Set item properties including position, rotation, z-index and display label.
- Switch between static and animated board modes.
- Create multiple animation frames within a single board for step-by-step tactic sequences.
- Control pitch orientation (horizontal or vertical).
- Save boards as tactical templates.

### Live Football and Data Browsing

- Browse competitions and leagues including fixtures and matchday results.
- View league table standings with position, points, form and goal difference.
- View top scorer standings per competition and season.
- Explore team and player enriched statistics including xG, xGA, PPDA, attacking and defensive performance metrics.
- Save and simulate league scenarios: enter fixture results and project the resulting table.
- Football data is cached via snapshots to reduce repeated external API calls and support faster page loads.

### Match Predictions and Analytics

xgGaffer boasts a technicaally diverse and advanced set of features, built on top of its prediction models. The prediction section is comprised of five distic sub-sections:

**Predictions Hub**

- Entry point listing available upcoming matches and prediction summaries.
- Links to individual match prediction pages with probability breakdowns.

**Match Prediction**

- Predicts the probability of home win, draw or away win for a specific match.
- Displays confidence levels and prediction strength indicators.
- Presents deterministic explanation cards derived from feature contributions and template logic.
- Shows team strength comparison strips and playing style profile cards.

**Match Intelligence Hub**

- Aggregated pre-match analysis view combining prediction data with contextual indicators.
- Player availability timelines showing injury and suspension status.
- Tactical context information derived from recent form and playing style data.

**Tactical Scouting Dashboard**

- Opponent scouting view designed for coaches.
- Presents playing style profiles, attacking and defensive tendencies and data-driven tactical pointers.

**Model Trust Centre**

- Model calibration charts showing predicted probability versus observed outcome frequency.
- Confidence versus accuracy scatter plots.
- Model quality reporting including accuracy metrics and backtesting results.

**Season Projection Centre**

- Projected points band charts showing likely season finish range for selected teams.
- Position probability matrices showing percentage likelihood of each finishing position.
- League-wide projected table based on model outputs.

**Odds Comparison**

- Side-by-side comparison of model prediction probabilities against market odds.
- Prediction versus market edge indicator cards.

### Referee Learning

- Structured Laws of the Game courses with multiple content types per module.
- Law extract content: written rule extracts with structured formatting.
- Drill content: practical application exercises.
- Scenario content: decision-making scenario walkthroughs.
- Quiz content: knowledge-check questions with scored results.
- Course results view showing per-module and overall performance.
- Progress tracking per user across all learning modules.
- Referee directory with profiles and individual statistics.

### Article Recommendations

- Personalised football article feed based on user interest profiles.
- External article sources with reputation and trust scoring.
- Topics with hierarchical category structure for filtering and recommendation matching.
- Author profiles with credibility metrics.
- Favourite articles list with toggle management.
- Like/dislike feedback on articles, authors and sites used to refine recommendations.
- Reading history tracking including time spent and scroll depth.
- User article preference profile: tracked interests, preferred topics, authors, sites and quality thresholds.
- Inferred interest scores updated from reading behaviour and explicit feedback.

### Social and Community Features

- Post feed with visibility controls: public, followers-only or private.
- Nested comment threads with reply support.
- Like/unlike feature on posts and comments.
- Hashtag support with usage count tracking.
- User mentions within posts and comments.
- Follow/unfollow users with follower and following counts.
- Block users to prevent content visibility.
- Content moderation: banned word filtering applied to posts on submission.
- Post reporting: users can report posts, with duplicate report prevention.
- Post view tracking for engagement analytics.

### Data Sync and Provider Integration

- Sync pipeline supporting multiple external football data providers: football-data.org, Transfermarkt, WhoScored, Understat and SofaScore.
- Scheduled and manually triggered sync runs per provider and dataset.
- Sync run tracking with status, row counts and error reporting.
- Provider health monitoring: rate limit tracking and API availability status.
- Versioned published data snapshots for reproducible reads.
- Canonical player database with player external identity resolution across providers with confidence scoring.
- Player enrichment snapshots publishing confirmed data scopes.

---

## System Architecture

The platform follows a layered full-stack architecture. The frontend is responsible for route-level pages and user interaction, while the backend exposes REST API endpoints, manages authentication, stores application data and runs background jobs. Machine learning and data processing services sit behind the API layer so predictions and football insights can be served to the user through stable application endpoints.

```md
![xgGaffer architecture diagram](docs/documentation/images/readme/system-architecture.png)
```

### Architecture principles

- **Separation of concerns:** backend apps are grouped by domain across 15+ Django apps covering clubs, teamsheets, tactics, predictions, referee learning, live football, articles, community and data sync.
- **Shared utilities:** `common/` backend and frontend folders centralise reusable logic including pagination, caching, response envelopes, constants and provider policies.
- **Multi-provider data layer:** a dedicated sync pipeline and canonical identity resolution layer abstracts multiple external football data sources behind consistent internal models.
- **Traceable analytics:** prediction explanations are generated from known model outputs, football statistics and templates rather than unsupported free-form responses.
- **Reproducible setup:** the README provides the minimum commands required to install and run the application locally.

---

## Technology Stack

| Layer            | Technology                                                           | Purpose                                                  |
| ---------------- | -------------------------------------------------------------------- | -------------------------------------------------------- |
| Frontend         | React, TypeScript, Vite                                              | Single-page application and user interface               |
| Backend          | Django, Django REST Framework                                        | REST API, authentication, business logic and permissions |
| Database         | PostgreSQL                                                           | Persistent relational data storage                       |
| Cache and queue  | Redis, Celery                                                        | Background jobs, scheduled tasks and cached data         |
| Machine learning | Python, pandas, scikit-learn, joblib                                 | Feature engineering, model training and inference        |
| Authentication   | httpOnly cookies/JWT-style token flow, email verification via Resend | Secure user access and account verification              |
| Media/storage    | [TODO: Cloudinary/S3/local media depending final setup]              | Uploaded images and media files                          |
| Deployment       | Docker, AWS/Railway or final deployment target                       | Hosted application environment                           |
| CI/CD            | GitLab CI/CD                                                         | Automated checks, test execution and deployment support  |

---

## Machine Learning and Prediction Layer

The prediction layer is one of the core technical components of xgGaffer. It is designed to provide football match predictions using structured football data rather than relying on an external large language model to make sporting decisions.

### Match outcome prediction

The match outcome model predicts the probability of:

- home win
- draw
- away win

The model uses engineered football features generated from historical football data. These include team-level and squad-level indicators such as expected goals (xG), expected goals against (xGA), attacking and defensive performance, PPDA (passes allowed per defensive action as a pressing indicator), team form and other match-related statistics.

The match outcome pipeline was trained on 10+ years of European top flight data and achieved approximately **55.5% accuracy**, significantly above the 33% random baseline for a three-class prediction problem and in competition
with professional Bookmakers who have set baselines varying between 50% and 65%.

### Model development workflow

```text
Raw football data
        |
        v
Canonical processed datasets
        |
        v
Feature engineering (xG, xGA, PPDA, form, rolling averages)
        |
        v
Model training and evaluation
        |
        v
Saved model artefacts (.joblib)
        |
        v
Prediction API endpoints
        |
        v
Frontend prediction widgets and insight pages
```

### Models explored

- Logistic Regression
- Random Forest
- Gradient Boosting
- Probability calibration (isotonic/Platt scaling)
- Model quality reporting: accuracy, calibration curves, confidence versus accuracy

### Additional prediction surfaces

Beyond the core outcome model, the prediction layer supports:

- **Backtesting:** evaluate historical model performance across past seasons.
- **Odds comparison:** compare model probabilities against bookmaker market odds.
- **Tactical scouting:** produce opponent-facing style and tendency profiles from enriched data.
- **Season projections:** aggregate match-level probabilities into projected season points ranges and finishing position distributions.

### Important note on model artefacts

Some generated files, such as large CSV datasets and `.joblib` model artefacts, may not be committed directly to the repository depending on file size and GitLab storage constraints. Where this applies, the Technical Guide should explain how to regenerate them or where they are stored for the final submission/demo.

---

## Deterministic Interpretation Layer

xgGaffer uses a deterministic interpretation approach for prediction explanations. This means the application avoids making untraceable claims about match outcomes. Instead, explanations are produced from known model outputs, football statistics, templates and feature contributions.

This design was chosen to improve:

- **Traceability:** every explanation maps back to data or model output.
- **Reliability:** the system avoids unsupported free-form claims.
- **Academic credibility:** analysts can inspect how explanations are generated.
- **Consistency:** similar prediction scenarios produce consistent explanation structures.

Example explanation flow:

```text
Prediction request
        |
        v
Feature generation (xG, form, PPDA, enrichment data)
        |
        v
Model probability output (home / draw / away)
        |
        v
Feature contribution / rule lookup
        |
        v
Template-based explanation
        |
        v
Frontend prediction insight card
```

[TODO: Add one short screenshot of a prediction explanation card]

```md
![Prediction explanation example](docs/documentation/images/readme/prediction-explanation.png)
```

---

## Repository Structure

The project is split into a Django backend and React TypeScript frontend. The structure below is condensed so that readers can quickly understand the important areas without reading every file in the repository.

```text
project-root/
├── build/
│   ├── backend/
│   │   ├── apps/
│   │   │   ├── articles/          # Article feed, recommendations, ratings, reading history
│   │   │   ├── clubs/             # Club management, membership, rosters, injuries, resources
│   │   │   ├── coaching/          # Coaching dashboard and base features
│   │   │   ├── community/         # Posts, comments, likes, hashtags, mentions, notifications
│   │   │   ├── integrations/      # External provider integration management
│   │   │   ├── laws/              # Laws of the Game learning and progress tracking
│   │   │   ├── livefootball/      # Competitions, standings, fixtures, top scorers, scenarios
│   │   │   ├── playerdata/        # Player and club season enrichment (xG, xGA, PPDA)
│   │   │   ├── players/           # Canonical player database and cross-provider identities
│   │   │   ├── predictions/       # ML models, prediction APIs and deterministic interpretation
│   │   │   ├── referee/           # Referee directory, profiles and statistics
│   │   │   ├── sync_pipeline/     # Provider sync runs, snapshots and source health tracking
│   │   │   ├── tactics/           # Canvas tactics board with frames and items
│   │   │   ├── teamsheets/        # Formation and teamsheet builder
│   │   │   └── users/             # Authentication, profiles, roles, follows and verification
│   │   ├── common/                # Shared utilities: cache keys, pagination, constants, helpers
│   │   ├── services/              # Provider query services and player overview aggregation
│   │   ├── backend/               # Django project settings, URLs, Celery configuration
│   │   └── manage.py
│   │
│   └── web-frontend/
│       └── src/
│           ├── common/            # Shared frontend components and state displays
│           ├── components/        # Reusable feature components (pitch, charts, widgets)
│           ├── pages/             # Route-level pages (25+)
│           ├── services/          # API clients for all backend apps
│           └── types/             # TypeScript type definitions
│
├── docs/
│   └── documentation/             # Final Technical Guide and User Manual PDFs
└── README.md
```

---

## Local Development Setup

These instructions are intended for a local development environment. The project can be run on Linux, WSL/Ubuntu on Windows, or native Windows PowerShell. Linux/WSL commands use `python3` and `source`, while Windows PowerShell commands usually use `python` and `.\Scripts\Activate.ps1`.

### Prerequisites

Install the following before running the project:

- Python 3.10+ or the final Python version used by the project
- Node.js and npm
- PostgreSQL
- Redis
- Git
- Docker and Docker Compose, if using the containerised setup

[TODO: Confirm final Python and Node versions from the actual project environment]

### Clone the repository

```bash
git clone https://gitlab.computing.dcu.ie/adenire2/2026-csc1097-adenire-2-oghinae-2.git
cd 2026-csc1097-adenire-2-oghinae-2/build
```

### Backend setup

```bash
cd backend
[Linux / WSL/ macOS]
python3 -m venv ../.venv
source ../.venv/bin/activate
python3 manage.py migratE

[Windows Powershell]
python -m venv ../.venv
..\ .venv\Scripts\Activate.ps1
python manage.py migrate

pip install --upgrade pip
pip install -r requirements.txt
```

### Create a Django superuser

```bash
python3 manage.py createsuperuser
```

### Frontend setup

From the `build` directory:

```bash
cd web-frontend
npm install
```

### Redis setup

If Redis is not already installed locally, it can be started using Docker:

```bash
docker run --name redis -p 6379:6379 -d redis:7
```

If a Redis container already exists, start it instead:

```bash
docker start redis
```

---

## Environment Variables

Create a backend `.env` file before running the application. The exact values depend on the local or deployed environment.

```text
build/backend/.env
```

Example variables:

| Variable                | Required                       | Purpose                                                 |
| ----------------------- | ------------------------------ | ------------------------------------------------------- |
| `SECRET_KEY`            | Yes                            | Django secret key                                       |
| `DEBUG`                 | Yes                            | Enables/disables Django debug mode                      |
| `DATABASE_URL`          | Yes                            | PostgreSQL connection string, if using URL-based config |
| `POSTGRES_DB`           | If using separate DB variables | PostgreSQL database name                                |
| `POSTGRES_USER`         | If using separate DB variables | PostgreSQL user                                         |
| `POSTGRES_PASSWORD`     | If using separate DB variables | PostgreSQL password                                     |
| `POSTGRES_HOST`         | If using separate DB variables | PostgreSQL host                                         |
| `POSTGRES_PORT`         | If using separate DB variables | PostgreSQL port                                         |
| `REDIS_URL`             | Yes                            | Redis connection for Celery/cache                       |
| `RESEND_API_KEY`        | If email verification enabled  | Resend email verification service                       |
| `CLOUDINARY_URL`        | If Cloudinary enabled          | Uploaded media storage                                  |
| `FOOTBALL_DATA_API_KEY` | If live sync enabled           | football-data.org integration                           |
| `ODDS_API_KEY`          | If odds refresh enabled        | Odds provider integration                               |
| `ALLOWED_HOSTS`         | Production                     | Allowed Django hostnames                                |
| `CSRF_TRUSTED_ORIGINS`  | Production                     | Trusted frontend origins                                |

[TODO: Replace this table with the final variable names from `settings.py`, `.env.example` or deployment configuration]

---

## Running the Application

### Run the backend API

From `build/backend`:

```bash
source ../.venv/bin/activate
python3 manage.py runserver
```

Default local backend URL:

```text
http://localhost:8000
```

### Run the frontend

From `build/web-frontend`:

```bash
npm run dev
```

Default local frontend URL:

```text
http://localhost:5173
```

### Run Celery worker

From `build/backend`:

```bash
source ../.venv/bin/activate
celery -A backend worker --loglevel=info
```

### Run Celery beat

From `build/backend`:

```bash
source ../.venv/bin/activate
celery -A backend beat --loglevel=info
```

### Common development URLs

| Service      | URL                           |
| ------------ | ----------------------------- |
| Frontend     | `http://localhost:5173`       |
| Backend API  | `http://localhost:8000`       |
| Django admin | `http://localhost:8000/admin` |

---

## Testing

The full testing strategy and results are documented in the separate Testing Document or in the Technical Guide, depending on the final documentation structure. This README only lists the main commands required to run the project checks.

### Backend tests

From `build/backend`:

```bash
source ../.venv/bin/activate
python3 manage.py test
```

### Backend system check

```bash
python3 manage.py check
```

### Frontend tests

From `build/web-frontend`:

```bash
npm run test
```

### Frontend production build check

```bash
npm run build
```

### Testing approach summary

The testing strategy includes:

- backend unit tests for models, serializers, services and utility logic
- backend API/integration tests for REST endpoints
- frontend component and service tests where implemented
- machine learning/data pipeline tests for feature generation and model services
- formal manual/system tests for complete user workflows
- CI/CD pipeline checks through GitLab

Testing evidence, expected results, actual results and discussion of failures/fixes should be included in the final Testing Document or Technical Guide.

---

## Deployment

[TODO: Update this section after final deployment is confirmed]

xgGaffer is designed to be deployable using a standard web application stack:

```text
Frontend static build
        |
        v
Nginx / web server / hosting platform
        |
        v
Django + Gunicorn backend
        |
        v
PostgreSQL database
        |
        v
Redis + Celery worker + Celery beat
```

A production deployment should include:

- environment variables set securely
- PostgreSQL database configured
- Redis running for cache/task queue support
- Django migrations applied
- static files collected
- Celery worker running
- Celery beat running for scheduled sync and cache refresh jobs
- model artefacts and required football data available to the backend
- HTTPS enabled
- `DEBUG=False`
- correct `ALLOWED_HOSTS` and CSRF settings

Common production commands:

```bash
python3 manage.py migrate
python3 manage.py collectstatic --noinput
python3 manage.py check --deploy
```

Detailed deployment steps should be placed in the Technical Guide or a separate deployment document, not expanded heavily in this README.

---

## Project Documentation

The final project documentation is located in:

```text
docs/documentation/
```

The required final PDF documents are:

| Document              | Purpose                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------- |
| Technical Guide       | Motivation, research, design, implementation, sample code, problems solved, results and future work |
| User Manual           | Installation instructions, user guide, screenshots and user-facing workflows                        |
| Testing Documentation | Testing results, implementation and strategy                                                        |

### Recommended documentation links

[TODO: Update links once final PDF filenames are confirmed]

- [Technical Guide](docs/documentation/technical_guide.pdf)
- [User Manual](docs/documentation/user_manual.pdf)
- [Testing Document](docs/documentation/testing_document.pdf)

---

## Known Limitations

- Some external football data features depend on API availability, rate limits and valid API keys.
- Large generated datasets and machine learning artefacts may need to be regenerated or supplied separately if they are not committed to the repository.
- Prediction outputs should be treated as football analytics support, not guaranteed betting advice.
- Free-tier deployment environments may limit background processing, memory usage, database size and response speed.
- Some features require seeded football data or sync pipeline data before they can be demonstrated properly.
- Final feature availability should be confirmed against the submitted version of the application.

---

## Future Work

Potential future improvements include:

- expanding live football coverage across additional leagues and seasons beyond the current supported competitions
- improving pre-match rolling feature generation for prediction models with more granular player-level input
- adding richer referee training scenarios with video or interactive elements
- improving deterministic football query handling and explanation template coverage
- adding more end-to-end frontend tests for important user journeys
- improving deployment monitoring, logging and cache observability
- enhancing social/community features including richer notification types and discovery
- improving mobile responsiveness and accessibility across all feature areas
- expanding the article recommendation engine with collaborative filtering signals

---

## Contributors and Acknowledgements

**Developers**

- Ehis Oghina
- Elizabeth Adeniran

**Supervisor**

- Dr. Ellen Rushe

**Institution**

- Dublin City University
- School of Computing
- CSC1097 Final Year Project

**Acknowledgements**

This project uses open-source tools and libraries including Django, Django REST Framework, React, TypeScript, Vite, PostgreSQL, Redis, Celery, pandas and scikit-learn. Football data integrations depend on the availability and terms of football-data.org, Understat and SofaScore. Email delivery uses the Resend service.

[TODO: Add exact data source acknowledgements required by the final Technical Guide]

---

## Licence

[TODO: Add final licence decision]

This repository is currently intended for academic assessment as part of a final year university project. If the repository is made public or reused beyond assessment, a formal licence should be added.

---

## README Maintenance Notes

Before final submission:

- Replace all `[TODO]` placeholders.
- Confirm all setup commands work from a clean clone.
- Confirm final URLs, environment variables and deployment commands.
- Add final screenshots to `docs/documentation/images/readme/`.
- Update documentation links to the final PDF filenames.
- Check that this README does not duplicate the Technical Guide or User Manual.
- Run all listed commands and update the testing section if command names differ.
