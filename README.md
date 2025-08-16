# Velocitas 🚀

**Integrating AI into your email experience to make reading and writing emails effortless.** Velocitas leverages AI to summarize emails, suggest replies in your unique writing style, and intelligently manage your inbox—all while keeping your data secure.  

[Website](https://iambodha.github.io/Velocitas/) | [GitHub](https://github.com/iambodha/Velocitas/tree/production)  

---

## Features ✨

- **Multi-user support** – Multiple users can log in and access their emails asynchronously.  
- **AI-powered email management**  
  - Automatic inbox summarization  
  - Personalized AI-generated email responses  
  - Context-aware email chat interface  
  - Intelligent email labeling  
- **Secure and scalable storage** – All emails and user data are stored in a PostgreSQL database.  
- **Extension-based interface** – Minimal, lightweight, and fully integrated into your browsing experience.  

---

## Screenshots  

*(Add screenshots of your extension and inbox here for a visual preview.)*  

---

## Installation & Usage 🛠️

**Note:** Currently, Velocitas cannot be fully public due to Google API verification restrictions.  

### 1. Clone the repository  
```bash
git clone https://github.com/iambodha/Velocitas.git
cd Velocitas
```

### 2. Set up your PostgreSQL database
- Create a PostgreSQL database.
- Update the database credentials in your `.env` file.

### 3. Run the API and extension
```bash
# Install dependencies
npm install

# Start the backend API
npm run server

# Start the frontend extension
npm run dev
```

### 4. Access your inbox
- Open the extension in your browser.
- Log in with your email account and enjoy AI-powered email management!

---

## Architecture 🏗️

Velocitas is built using a **microservices architecture**:

- **API** – Handles authentication, threading, and multi-user support.
- **Database** – PostgreSQL for secure, scalable email storage.
- **Frontend** – Next.js extension interface for minimal and aesthetic inbox management.
- **AI services** – Summarization, reply suggestions, and automatic labeling.

---

## Contributing 🤝

Contributions are welcome! Feel free to open issues or submit pull requests. Please adhere to clean code standards and maintain secure handling of user data.
