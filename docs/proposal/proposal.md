# School of Computing &mdash; Year 4 Project Proposal Form

## SECTION A

|                     |                                 |
|---------------------|---------------------------------|
|Project Title:       | iFoot                           |
|Student 1 Name:      | Elizabeth Adeniran Adetipe      |
|Student 1 ID:        | 22371553                        |
|Student 2 Name:      | Ehis Oghina                     |
|Student 2 ID:        | 22506739                        |
|Project Supervisor:  | Ellen Rushe                     |

## SECTION B

### Introduction
This project covers sports analysis, education, and social interaction. It is a user-based web/mobile app that allows users from different backgrounds to engage with social, educational and analytical content. The project will cover player habits, match tactics, referee improvement methods, social connection, mental support. 

### Outline

> Outline the proposed project.
The proposed project is a sports-based web application/mobile application where fans, players, parents, referees and coaches can interact with a variety of features related to the sport. The project aims to close the gap between the popularity of football in the country and the resources available to participants of the game. The first area this project tackles is the lack of community spaces for people to engage with. Our application will provide group and private messaging features for people to connect with each other and discuss topics. We will also enable users to create discussion threads where users can share their thoughts on current, past or future events. Increased conversation sparks ideas, ultimately leading to the standard of knowledge and enthusiasm surrounding the game to increase. 
This project will also offer referees a space to hone their skills. Referees are often crticised for being out of touch with general fan bases and improve their communication skills, knowledge of the games laws and fitness will enable them to level up as officials and control games. A referee that communicates their thoughts clearly, is composed and calm, and can keep up with the ran of play is appreciated by fans and players alike. A higher standard for our officials means a higher standard for our games.
A area of focus for this project is for coach development, tactical improvement and analysis and game-relevant predictions driven by data. Our application will connect to numerous data sources that provide information based on player and team performances. We will train prediction models on these data sets and use a LLM to interpret the predictions and provide accurate data-backed interpretations to users. For the users this will look like entering questions, queries or opinions into an interface, sometimes with accompaning figures and receiving a detailed and accurate response. This project will assist coaches in developing proven ideas and will cut out time wasted experimenting and what we know is destined to fail. This assistance along with the range of helpful features we have available will raise the bar in terms of what is seen to be a competent and knowledgable coach. Coach's will have access to features such as tactics boards, teamsheets, on-site club management, stats-trackers, suggested articles and videos, powerpoint and file uploads, and pre and user made learning courses.    

### Background
Our 3rd Year project was centred around education and sports. Our work last year inspired us to create a more complex and practical application in this same field. 
An issue with modern application/websites is that it's difficult to find a platform that offers multiple useful tools at the same time. Features are often split between
multiple applications and sometimes hidden behind paywalls. We are covering multiple aspects in our project looking at player perspectives, coaching tools, referee education,
and social interactions. 
Football in Ireland is increasing in popularity but we are still lacking the educational resources needed to raise the standard of our game. The insights that will be 
available on our application will help coaches make better informed decisions. 

### Achievements
The project will provide social and educational functions. Users will be able to create groupchats or message each other privately, track things in a calendar, interact with other users social profiles, engage in discussion threads and avail of mental health support. The users will be any football enthusiasts, players, coaches, referees or casual users who are intersted in interacting with people in a similar field and availing of the our features. There will be sections of the app where we expect users to be of a specific role e.g. the users in the coaching section are expected to be aspiring and established football managers who are looking to improve their gameplans, gain insights on player performance, or plan for upcoming games. The Referee section will also provide functions that are specifically beneficial to referees such as Laws of The Game quizzes, fitness drills, relevant articles and emotional/control training or advice.


### Justification
It will be useful because there is a large group of people who will benefit from the features available. They will also have the opportunity to interact with each other, fostering a helpful and positive community in the sporting space. Players will be able to take on instructions through an easy to understand method, coaches will be able to develop their ideas with helpful and detailed insights and referees will be able to improve their fitness and knowledge on game rules. The application is useful to people that take roles in every area of the game. 
It will be useful immediately. The application is currently relevant and will remain so indefintely as the global phenomanon that is the game of football continues to rise in populairty. The rising popularity drives change and improvement in method as competition becomes more and more fierce. As a result the application will be useful to a vast number of users seeking to learn and socialise straight away and will remain so.
It will be useful in every country/city where football is played and people seek to know more about it. There are no location restraints for where this application will be relevant as football is an international sport. In schools, academies, local clubs, and social circles this application will be useful for fans, parents, players, coaches, and referees. 
The application will prove itself useful by offering users relevant and helpful content. It will achieve the goals set out e.g. provide quizzes and fitness drills for referees, coaching insights for managers and social opportunities for all users. 

### Programming language(s)
Python, TypeScript, CSS, HTML

### Programming tools / Tech stack
Frontend: Typescript(React)
Backend: Python(Djano) + DRF(Django REST Framework), Celery for async
ML: Python services (FastAPI) on Docker, models via SageMaker, Python scikit-learn(decision trees, logistic regression)


### Hardware
Media Processing Nodes: For Powerpoints, slides need to be rendered, videos transcoded and adaptive streaming required
IoT Devices: For some types of data collection, wearable devices will feed data into iFoot. Integreation will require device gateways or specialised BLE/WIFI hardware

### Learning Challenges

> List the main new things (technologies, languages, tools, etc) that you will have to learn.
We will have to learn how to train prediction models and integrate them into our application. 
We will have to learn how scrape data.
We will have to learn how to connect our application to pre-exisitng API's.
We will have to learn how to intergate a LLM into our application to interpret the predictions.

### Breakdown of work
Elizabeth:
Elizabeth will focus on developing the social section of the application. She has previous experience creating discussion threads and integrating social features into applications. As a result she will focus on developing the messaging features, discussion threads, social profiles and mental health support hub in the design hub. 
Elizabeth will also format the LOG quizzes in order to make the quizzes engaging for users. 
Ehis:
Ehis will focus on developing the coaching and reffing section of the app. He has experience using and developing football-based tools and will implement the tactics boards, teamsheets, stats trackers and other features. He will also work on the coaching courses, referee fitness drills and situational videos.
Both students will work on developing the machine learning aspects of the application and training prediction models that will be used for providing insights. 

### Risk Register

> You are to complete a risk register to demonstrate how you will account for the potential risks (i.e. something going wrong) when youa re working on your proiject. 
> The purpose of a risk register is to identify potential issues beforehand and plan mitigation strategies to ensure the success of the project. 
> The reisks are different for each project by some examples include 

> if you are using physical components (e..g sensors), what happens if they never arrive, or if they break, or if they are not suitable?
> if you are creating an AI/ML method , what happens if there is no suitable training data, or if the model performs poorly after training? 

|  # | Risk                                                          | Description                                                                                                                    | Likelihood               | Severity     | Mitigation                                                                                                                                                                                                                      |
| -: | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  1 | **Insufficient or low-quality data for prediction models**    | Licensed feeds don’t cover target leagues/levels; club uploads are sparse/inconsistent → models can’t learn reliable patterns. | **Medium–High (40–60%)** | **High**     | Secure tiered data providers early; define strict ingest schemas & validators; start with heuristics/baselines; run data gap analysis per league; create data-collection UX (CSV templates, coach prompts) to improve coverage. |
|  2 | **Model underperforms or drifts in production**               | Offline metrics look good but real-world recommendations don’t translate; opponent behavior changes → degraded advice.         | **Medium (30–40%)**      | **High**     | A/B test vs heuristics; set acceptance KPIs (engagement, success proxies); monitor drift & recalibrate cadence; champion–challenger setup; include explainable rules as backstop; allow coaches to give feedback to retrain.    |
|  3 | **Licensing/compliance breach from scraping or data use**     | Terms of use or GDPR constraints violated (e.g., scraping without permission, profiling minors).                               | **Medium (25–35%)**      | **Critical** | Prioritize licensed APIs; legal review of sources; scraper allowlists & robots.txt respect; data processing agreements with clubs; age-gating & parental consent flows; PII minimization and DSR automation.                    |
|  4 | **Matchday traffic spikes overwhelm realtime features**       | Sudden surges during big games impact chat, tactics boards, and RAG queries (timeouts, message loss).                          | **Medium (30–50%)**      | **High**     | Load test with k6; autoscaling with per-service SLOs; Redis + CDN caching; degrade gracefully (queue heavy jobs, cap RAG calls, fallback to cached insights); sharded WebSocket clusters; circuit breakers and rate limits.     |
|  5 | **Safety/moderation failure in social & mental-health areas** | Toxic content or harmful advice slips through; reputational and user-safety impact.                                            | **Low–Medium (15–25%)**  | **Critical** | Multi-layer moderation (keyword rules + ML + human review), crisis-resource surfacing (no diagnosis), report/block tools, audit trails, age-appropriate defaults, periodic red-team reviews, and clear community guidelines.    |


#### Student 1
Programming Tools/Tech Stack, Hardware, Learning Challenges, Risk Register

#### Student 2
Introduction, Outline, Background, Achievements, Justification, Programming Languages, Breakdown of work
