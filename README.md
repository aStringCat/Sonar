# 🛰️ Sonar: Python Code Similarity Detector

A powerful tool designed to detect plagiarism and measure similarity in Python codebases. It provides a clean, user-friendly desktop interface powered by a robust backend API, making it easy to analyze code for originality.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Framework-FastAPI-blueviolet?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/UI-PyQt6-green?logo=qt" alt="PyQt6">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
</p>

---

### 🎯 Project Purpose

> * **🧑‍🏫 Academic Integrity:** Helps educators efficiently check student assignments, quickly identifying similar code to maintain a fair academic environment.
> * **🏗️ Codebase Management:** Helps development teams analyze repositories to identify duplicated code, promoting refactoring and maintaining a clean architecture.
> * **🎓 Learning & Development:** Helps programmers compare their solutions with reference implementations to understand different approaches and improve their skills.

---

### 💻 Technology Stack

The project follows a client-server architecture, separating the user interface from the core analysis logic.

<br>

<details>
<summary><b>⚙️ Backend</b></summary>

| Technology     | Description                                                                                                                              |
| :------------- | :--------------------------------------------------------------------------------------------------------------------------------------- |
| **FastAPI** | <img src="https://img.shields.io/badge/Framework-FastAPI-blueviolet?logo=fastapi" alt="FastAPI"> <br> A modern, high-performance Python web framework for building the RESTful API. |
| **Scikit-learn**| <img src="https://img.shields.io/badge/Library-Scikit--learn-orange" alt="Scikit-learn"> <br> Uses `TfidfVectorizer` and `cosine_similarity` to quantify the similarity between code files. |
| **SQLAlchemy** | <img src="https://img.shields.io/badge/ORM-SQLAlchemy-red" alt="SQLAlchemy"> <br> Used to persist code submission records and analysis results to the database.        |
| **SQLite** | <img src="https://img.shields.io/badge/Database-SQLite-blue" alt="SQLite"> <br> A lightweight, local database for storing submission history.                  |

</details>

<details>
<summary><b>🖥️ Frontend</b></summary>

| Technology | Description                                                                                                                                  |
| :--------- | :------------------------------------------------------------------------------------------------------------------------------------------- |
| **PyQt6** | <img src="https://img.shields.io/badge/UI-PyQt6-green?logo=qt" alt="PyQt6"> <br> A powerful, cross-platform GUI toolkit for building a feature-rich desktop application. |
| **Requests** | <img src="https://img.shields.io/badge/Library-Requests-green" alt="Requests"> <br> Used to send HTTP requests to the backend API to submit jobs and retrieve results. |

</details>

---

### 📋 Python Requirements

To run this project, you will need to install the following Python packages. It's recommended to create a `requirements.txt` file for both the backend and frontend.

> #### **Backend `requirements.txt`**
>
> ```txt
> fastapi
> uvicorn[standard]
> sqlalchemy
> scikit-learn
> python-multipart
> ```

> #### **Frontend `requirements.txt`**
>
> ```txt
> pyqt6
> requests
> ```

---

### 🚀 How to Run on macOS

A `run.sh` script is provided to simplify the launch process.

1.  **Save the Script:** Save the content below as `run.sh` in the project's root directory.
2.  **Grant Permissions:** In your terminal, run `chmod +x run.sh`.
3.  **Execute the Script:** Run `./run.sh` to start the entire application.
