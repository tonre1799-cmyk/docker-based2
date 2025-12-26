# Kubernetes Migration Guide

This document outlines the path to migrating from **Docker Compose (MVP)** to **Kubernetes (Scale)**.

## 🚦 When to Migrate?
1.  **Scale:** You have > 50 cameras and single-server vertical scaling (adding RAM) is too expensive.
2.  **Availability:** You need Zero Downtime updates or auto-healing.
3.  **Hardware:** You want to run dedicated GPU nodes for ML Workers and cheap CPU nodes for the Database.

## 🗺️ Mapping: Compose -> K8s

| Service | Docker Compose | Kubernetes Resource | Notes |
| :--- | :--- | :--- | :--- |
| **All** | `network:` | `Service` (ClusterIP) | Internal networking. |
| **Postgres** | `container` | `StatefulSet` + `PVC` | Needs persistent disk. |
| **Redis** | `container` | `Deployment` | Can be stateless if cache only. |
| **Minio** | `container` | `StatefulSet` + `PVC` | Or switch to AWS S3 / Google Storage. |
| **Vault** | `container` | `Deployment` | Stateless app logic. |
| **ML Worker**| `container` | `Deployment` + `HPA` | **Horizontal Pod Autoscaler** is the magic. |

## 🚀 Scaling Strategy (The "Magic")

In K8s, we will replace the static `ML Worker` count with **KEDA** (Kubernetes Event-driven Autoscaling).

*   **Trigger:** Redis Queue Length > 100 items.
*   **Action:** K8s launches 10 more ML Worker pods automatically.
*   **Result:** Backlog clears -> Pods terminate to save money.

## ⚠️ Preparation Steps (Do these NOW)
1.  **Health Checks:** Ensure every container has a valid `/health` endpoint (Done).
2.  **Statelessness:** Ensure ML Workers never save local files; always upload to Minio/S3 immediately (Done).
3.  **Config Maps:** Stop using `.env` files; move to environment variables injected by the orchestrator (Done).
