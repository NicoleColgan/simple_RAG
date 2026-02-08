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

## Dockerizing the UI

### 1. The Multi-Stage Build (The "Construction" vs. "Storefront" logic)

- The Build Stage: To create a React app, you need "heavy machinery" like the Node runtime, NPM for dependencies, and compilers for TS/JSX. We use these to turn our raw source code into a dist/ folder.
- Why drop the source code? We don't need CSS or Source Code in the final phase because the compiler has already bundled and minified everything into tiny, browser-ready files. Keeping the raw source code in the final image is a security risk and wastes space.
- Layer Caching: By copying package.json and running npm install before copying the rest of the code, Docker caches the dependencies. If the code changes but the libraries don't, Docker skips the 5-minute install and finishes in seconds.

* When you run your build, Vite takes all your React components and css and converts them to static files. The entry point the the static `index.html` file.
* The browser is the one executing the UI updates (like `useState`). Nginx just hands the files to the browser like a delivery service
* We can techincally use the Node image to host the site to, infact we do this in dev when running `npm run dev` but in production, thats not great. ITs better to use a high performance web server like Nginx.
* **Performance**: Nginx is a high-performance web server written in C. It is purpose-built to handle thousands of concurrent connections with a tiny memory footprint.
* **Security**: Nginx has a much smaller "attack surface" than Node. Because it doesn't execute code—it only moves files to the browser—it is significantly harder to exploit.
* **Built-in Features**: By using Nginx, we get "production-ready" features for free, such as:
  - Compression (Gzip): Shrinks file sizes for faster loading.
  - Caching: Tells browsers to save assets locally to save bandwidth.
  - Rate Limiting: Protects the site from being overwhelmed by too many requests.

### 2. The Production Stage (The "Nginx" phase)

- Switching to Nginx: Once the build is finished, we no longer need Node.js. We switch to a lightweight Nginx image because it is purpose-built to serve static files (HTML/JS/CSS) extremely fast.
- How does Nginx know what to do? Nginx doesn't "run" the code like Python or Node does. It just sits there like a librarian. When a user visits your URL, Nginx says, "I have those files right here in /usr/share/nginx/html," and hands them to the browser. The browser is actually the one that "runs" the React app.

* The "Clean Slate" Final Phase: When the Dockerfile hits the second `FROM` instruction, Docker completely wipes the environment. It discards the Node.js runtime, the `node_modules` folder, and all your raw source code. Only the finished, compiled assets are "plucked" from the build stage and moved into the Nginx image.
* We move the build to `/usr/share/nginx/html` because that is exactly where Nginx is pre-configured to look for files to serve.

### 3. Hardened Security & Non-Root

- Config: We used a Hardened Image (DHI). This means security experts already configured the logs, worker processes, and user permissions.
- Since the container runs as a non-root user (User 65532) for security, it cannot use "privileged" ports like 80. It is pre-configured to listen on 8080.
- Mapping: Because the container uses 8080, we map our local port to match:

```bash
docker run -p 8080:8080 simple-rag-frontend:latest
```

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
