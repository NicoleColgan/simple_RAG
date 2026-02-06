# Frontend - React (Vite + TypeScript)

[RAG Interface](./interface.png)

## About react

React allows us to build a **declarative UI**. Instead of manually telling. Instead of manually telling the browser, "delete this. Add that", we simple update the **state** (`useState`), and React efficiently handles the UI update.

## ⚡ Why Vite over `create-react-app`?

- **Speed:** Vite uses **SWC** (a Rust-based compiler) and native browser ES modules. It starts in milliseconds, while CRA takes minutes.
- **Modern Standards:** CRA is now deprecated. Vite is the 2026 industry standard for professional React development.

## 🛠️ Implementation & Setup

### 1. Environment Preparation

If working behind a corporate firewall or proxy, ensure your registry is pointed to the public internet:

```bash
npm config set registry [https://registry.npmjs.org/](https://registry.npmjs.org/)
```

## 2. Project Scaffolding

We used Vite to scaffold the project with the react-ts (TypeScript) template:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

## 3. Enabling CORS (Cross-Origin Resource Sharing)

Why? Browsers block scripts from one origin (Port 5173) from talking to another (Port 8000) for security. We enabled CORSMiddleware in FastAPI to "trust" our frontend, allowing the two services to communicate.

---

## 🧠 Key Technical Concepts

### 🔄 The "Async" Frontend vs. "Sync" Backend

Even if the Python /query endpoint is synchronous, we must use async/await in React.

- **The Promise**: fetch() returns a Promise (a placeholder for future data). We await it so the browser doesn't freeze while waiting for the network.
- **Double Await**: We await the response first, then await response.json() to parse the raw HTTP stream into a JavaScript object.

### 🍱 State Management & UX

Using useState(), we manage the **Lifecycle of a Request**:

1. **Disabled State**: When a user clicks "Ask Bot" we set loading to true. This disables the buttons so the user cannot spam the backend with multiple requests while the LLM is thinking.
2. **Conditional Rendering**: We use {answer && <p>{answer}</p>} to ensure the response box only appears once the data has actually arrived.

### 📤 Multi-File Ingestion

The handleUpload function processes a ChangeEvent<HTMLInputElement>.

- **File Extraction**: We extract the FileList from `e.target.files`.
- **FormData**: Since we are sending files (not just text), we use the FormData object.
- **List Mapping**: We loop through the files and append each to the same 'files' key. This is required for FastAPI to correctly interpret the data as a list[UploadFile].

---

## 🧪 Testing the UI

1. Start the backend: `uvicorn main:app --reload`
2. Start the frontend: `npm run dev`
3. Upload a PDF/TXT via the Ingest button (optional - we already have files stored).
4. Once the success alert appears, ask a question in the text area to verify the RAG retrieval.

## Implementation

- connect to proxy if neccessarry
- reset npm registry if neccessary
  use vite to create react frontend. This command does your npm install and starts the server too
- Vite is better than create-react-app - but why???
- enable cors in the fast api app so this react app can reach the endpoints - why????

```bash
npm create vite@latest frontend -- --template react

# manually start the server
npm run dev
```

- Edit `App.tsx` which is the main page
- return simple ui by writing jsx
- add a text area that the user can type the query to send to the query endpoint then when the user submits it it triggers the handler function which sends a post request to the `/query` endpoint
- we await this response even though the `/query` endpoint isnt async cause fetch returns a promise???? so we need to wait for the promise to actually resolve to get the data
- we then await the `.json()` function otherwise we wont have jeon data
- set the response and use conditional rendering to render it
- while processing the request, disable to button so the user cant submit another request since the backend isnt async. use `useState()` for this
- Add an input to upload files and allow multiple files of type pdf and text, again disabling it if the users request is being processed
- the `handleUpload` function takes in a `ChangeEvent<HTMLInputElement>` which is a file???? then we extract the files from it, and convert it to the 'files' list that the endpoint expects.
- send a post request to the ingest endpoing with the files, convert response to json and update the user with the response
