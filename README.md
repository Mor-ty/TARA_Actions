
# Project Title

A brief description of what this project does and who it's for

#  Automated HAR → JMeter Test Pipeline

This repository contains a fully automated system to convert **HAR files into JMeter tests**, execute them inside **Docker**, generate **HTML performance reports**, and produce **AI-based insights** on test results.


---

#  1. Manual Workflow — `Run Load Test Manually`
Trigger: **workflow_dispatch**

Use this workflow when you want to upload any HAR file manually and run the pipeline on demand.

### ✔ Features
- Upload HAR file as manual input  
- Converts HAR → JMX  
- Runs JMeter inside Docker  
- Generates `.jtl` results file  
- Builds complete HTML performance report  
- Produces AI insights from `.jtl`  
- Uploads artifacts (JMX + Report + Insights)

---

#  2. Automatic Workflow — `Auto Run on HAR Push`
Trigger: **push**

Whenever you push a `*.har` file into the repository, this workflow automatically:

###  What It Does
1. Detects **only the HAR file changed in the latest commit**
2. Converts HAR → JMX
3. Executes a Dockerized JMeter load test
4. Generates results + HTML report
5. Runs AI analysis on JTL output
6. Uploads artifacts for download

###  HAR Detection Logic
The workflow detects the latest `.har` file by checking the files modified in the last commit:

```bash
git diff --name-only HEAD^ HEAD | grep ".har"

