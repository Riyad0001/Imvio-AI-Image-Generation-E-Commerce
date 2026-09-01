# IMVIO Backend

Backend API for **IMVIO** — an AI-powered art generation and print-on-demand platform. It handles user authentication, AI image synthesis across multiple providers, credit wallet management, Stripe billing/subscriptions, and print fulfillment through Gelato.

---

## Features

- **AI Image Generation**: Multi-engine support including OpenAI (DALL-E), Stability AI, and Google Gemini with customizable styles, aspect ratios, and regeneration options.
- **Credit & Wallet System**: User wallets with credit deduction per generation, balance tracking, and pack purchases.
- **Subscriptions & Billing**: Stripe integration for recurring subscription plans, one-time credit top-ups, invoices, and webhooks.
- **Print-on-Demand (Gelato)**: Product catalog (canvas, posters, apparel), dynamic size/pricing calculations, mockup previews, and automated order fulfillment.
- **Authentication**: JWT-based auth (access/refresh tokens with blacklisting), Google OAuth login, and OTP password recovery.
- **Admin Dashboard**: Modern Django Unfold interface with custom dashboard stats, revenue overview, and order tracking.

---

## Tech Stack

- **Framework**: Django 5.2 & Django REST Framework (DRF)
- **Database**: PostgreSQL (production) / SQLite (local development)
- **Task Queue**: Celery & Redis
- **Auth**: SimpleJWT, Google OAuth
- **External Integrations**:
  - AI: OpenAI, Stability AI, Google Gemini
  - Payments: Stripe
  - Fulfillment: Gelato API
  - Email: Brevo (SMTP)

---

## Getting Started

### 1. Prerequisites

- Python 3.10+
- PostgreSQL or SQLite
- Redis (optional, for background tasks)

### 2. Clone and Setup Environment

```bash
# Clone repository
git clone <repo-url>
cd IMVIO

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=*
FRONTEND_BASE_URL=http://localhost:5173

# Database (if using PostgreSQL)
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=strongpassword
DB_HOST=localhost
DB_PORT=5432

# Third-Party APIs
OPENAI_API_KEY=your_openai_key
STABILITY_API_KEY=your_stability_key
GEMINI_API_KEY=your_gemini_key
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
GELATO_API_KEY=your_gelato_api_key
```

### 4. Database Migrations & Superuser

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/v1/` and the admin panel at `http://127.0.0.1:8000/admin/`.

---

## Key API Endpoints

| Route | Description |
| --- | --- |
| `/api/v1/signup/`, `/api/v1/login/` | User registration and JWT login |
| `/api/v1/social/google/` | Google OAuth sign-in |
| `/api/v1/profile/credits/` | Check user credit balance |
| `/api/v1/images/generate/` | Generate AI artwork |
| `/api/v1/images/history/` | View user generation history |
| `/api/v1/payments/buy-credits/` | Purchase credit packages |
| `/api/v1/subscribe/` | Create Stripe subscription checkout session |
| `/api/v1/product-types/` | List print products and sizes |
| `/api/v1/orders/create/` | Place a print-on-demand order |

---

## License

Private repository. All rights reserved.
# Imvio-AI-Image-Generation-E-Commerce
