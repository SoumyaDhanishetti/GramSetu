# GramSetu 🌱
### Connecting Rural Communities, Farmers, and Local Entrepreneurs

GramSetu is a web-based platform designed to support rural development and livelihoods by connecting farmers, local producers, women entrepreneurs, self-help groups (SHGs), and job seekers.

The project aims to improve access to agricultural information, local markets, employment opportunities, and digital tools for rural communities.

## 🚀 Key Features

### 1. Farmer Marketplace
- Publish crop listings with quantity, price, and location.
- Display contact details for interested buyers.
- Search available crop listings.
- Support listing photos where implemented.

### 2. Rural Products Marketplace
- Showcase locally made products, including handmade goods and food products.
- Support women entrepreneurs and SHGs in reaching potential customers.
- Display product details, prices, and seller information.
- Search product listings.
- Provide listing management controls where implemented.

### 3. Rural Employment
- Display local job and work opportunities.
- Help job seekers discover opportunities in their communities.
- Provide search and listing-management features where implemented.

### 4. Smart Farming
- Provide a dedicated farming information page.
- Include experimental leaf-image screening when the required AI dependencies and model are configured.
- Encourage farmers to seek expert confirmation before making crop-treatment decisions.

**Important:** AI screening is experimental and may produce incorrect results. It is not a substitute for advice from qualified agricultural experts.

## 🛠️ Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **AI:** Optional image-classification component, depending on configuration
- **Version control:** Git and GitHub

## 📋 Requirements

- Python installed on your computer
- pip, the Python package installer
- Git, if cloning the repository
- Internet access to install dependencies

Use the Python version supported by the dependencies in this repository.

## ⚙️ Installation and Setup

### Step 1: Clone the repository

Open a terminal and run:

```bash
git clone https://github.com/SoumyaDhanishetti/GramSetu.git
cd GramSetu
```

If you already have the project on your computer, open a terminal in your existing GramSetu folder instead.

### Step 2: Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv venv
```

### Step 3: Install dependencies

```powershell
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

If a separate AI requirements file exists, install it only if you need the AI functionality and have checked its compatibility.

### Step 4: Run the application

```powershell
.\venv\Scripts\python.exe app.py
```

### Step 5: Open GramSetu

Open the local address shown in your terminal. It is typically:

http://127.0.0.1:5000

Stop the development server by pressing `Ctrl+C` in the terminal.

## 🔐 Environment Variables and Secrets

Review the application code and configuration files to identify any environment variables required by the current implementation.

- Never publish passwords, API keys, private credentials, or real users' private information.
- If environment variables are required, document their exact names and provide placeholder values in an example configuration file.
- Do not add variables that the application does not actually use.

## 🗂️ Project Structure

The main project files include:

```text
GramSetu/
├── app.py
├── templates/
├── static/
├── requirements.txt
├── README.md
├── LICENSE
├── TECHNICAL_DESIGN.md
└── TEST_PLAN.md
```

The structure above is illustrative. Keep any additional files and folders already present in your actual project.

## 🧪 Testing

Use `TEST_PLAN.md` to verify the implemented functionality before deployment.

Test the following where supported:

- Application startup and page navigation
- Crop and product listing creation
- Search functionality
- Listing-management controls and authorization
- Image uploads
- Database persistence after restarting the application
- Smart-farming functionality, if enabled
- Live website behavior after deployment

Record the actual test results. Do not mark a test as passed until it has been performed.

## 🌍 Deployment Considerations

Before deploying GramSetu:

1. Verify that all required dependencies are declared.
2. Back up the database and uploaded images.
3. Keep credentials and secrets out of GitHub.
4. Configure persistent storage for the database and uploaded images if the hosting provider uses temporary storage.
5. Use production settings and disable Flask debug mode.
6. Test the live website after deployment.

## ⚠️ Limitations

- Listings, prices, contact information, and job opportunities may be user-submitted and unverified.
- AI-based leaf screening may be inaccurate.
- Security, privacy, accessibility, and scalability must be evaluated before production use.
- Features described in this document should be verified against the current implementation.

## 📄 Documentation

- `TECHNICAL_DESIGN.md` — architecture and technical design.
- `TEST_PLAN.md` — functional test cases and test results.
- `LICENSE` — open-source licensing terms.

## 🤝 Contributions

Contributions are welcome in accordance with the project's license. Please test changes before submitting them and avoid including real personal data or secrets.

## 📜 License

This project is distributed under the license specified in the `LICENSE` file.
