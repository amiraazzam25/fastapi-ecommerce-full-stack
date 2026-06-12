# E-Commerce Full-Stack Application

This is a comprehensive full-stack e-commerce application built with a modern technology stack. It features a robust FastAPI backend, a seamless HTML/JS/CSS frontend, and uses SQL Server for data persistence alongside Redis for fast, in-memory caching operations.

## Features
* **User Authentication & Role Management:** Secure JWT-based registration and login with user/admin role restrictions.
* **Product & Category Management:** Create, read, update, and delete products and categories (Admin only), with robust search and filtering.
* **Shopping Cart:** Redis-backed temporary shopping cart for fast checkout flows.
* **Order Processing:** Place, track, cancel, and ship orders while intelligently managing product stock.
* **Monitoring & Observability:** Real-time system monitoring dashboard, Prometheus metrics integration, and structured application logging.
* **Fully Dockerized:** Seamlessly containerized to run the API, frontend, Redis, and metrics stack with a single command.

---

## 🚀 Setup & Installation Instructions

### Prerequisites
1. **Docker & Docker Compose:** Ensure you have Docker Desktop installed on your machine.
2. **SQL Server:** You need a running instance of Microsoft SQL Server (can be running natively on Windows or in another container).
3. Ensure your SQL Server has **TCP/IP connections enabled** and port `1433` is open in your firewall.

### 1. Database Configuration
1. Open the `main_app/.env` file.
2. Ensure your connection string variables are properly set to match your SQL Server setup. For example:
   ```env
   DB_DRIVER=driver_name
   DB_SERVER=host.docker.internal,1433
   DB_NAME=db_name
   DB_USER=db_username
   DB_PASSWORD=db_password
   SECRET_KEY=your_secret_key
   ```
*(Note: `host.docker.internal` allows the Docker container to communicate with the SQL Server running on your host Windows machine).*

### 2. Building and Running with Docker
The easiest way to run the entire application—which includes the FastAPI backend, the Frontend serving logic, Redis cache, Prometheus, and Grafana—is using Docker Compose.

1. Open your terminal and navigate to the `main_app` directory:
   ```bash
   cd main_app
   ```
2. Build the Docker images and start the containers in detached mode:
   ```bash
   docker-compose up --build -d
   ```
3. Wait a moment for the containers to start up. You can check the logs using:
   ```bash
   docker-compose logs -f app
   ```

### 3. Accessing the Application
Once the containers are running successfully, you can access the various services in your browser:
* **Frontend Web App:** [http://localhost:8000/](http://localhost:8000/)
* **Interactive API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Monitoring Dashboard:** [http://localhost:8000/monitoring.html](http://localhost:8000/monitoring.html)
* **Grafana (Metrics visualization):** [http://localhost:3000/](http://localhost:3000/)

### 4. Stopping the Application
To stop all running containers safely, run:
```bash
docker-compose down
```

---

## 👥 Team Member Roles

This project was built collaboratively by our engineering team:

* **Youssef Waheed**
  Built the foundational structure, designed the database and ORM models, and acted mainly as the consultant and architect for the project.
  
* **Maria Gerges**
  Worked comprehensively on all files and logic related to the shopping cart, including the Redis caching implementations.
  
* **Yousef Medhat**
  Developed all files and logic related to the order processing system and order item management.

* **Amira Azzam**
  Developed the security layer, working on all related files to users, JWT authentication, and authorization.

* **Ali Abdo**
  Worked on all related files to products, including CRUD operations, stock management, and filtering.
  
* **Amr Yasser**
  Worked on all related files to categories and developed the entire frontend application and user interface.
