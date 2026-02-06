import { useState, ChangeEvent } from "react";

function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [ingesting, setIngesting] = useState(false);

  const askQuestion = async () => {
    if (!query) return;
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query }),
      });
      const data = await response.json();
      setAnswer(data.response);
    } catch (error) {
      console.error("Something went wrong contacting the server: ", error);
      setAnswer("Oops, something went wrong");
    } finally {
      setLoading(false);
    }
  };
  const handleUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIngesting(true);
    const formData = new FormData();

    // Loop through files and append to the 'files' key your FastAPI expects
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const response = await fetch("http://localhost:8000/ingest", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        alert(
          `Success!\nFiles: ${data.filenames.join(", ")}\nChunks ingested: ${data.chunks_ingested}`,
        );
      } else {
        alert(`Error uploading files: ${data.error_msg || "Unknown Error"}`);
      }
    } catch (error) {
      alert("No response from server - make sure it's running");
    } finally {
      setIngesting(false);
      // reset input
      e.target.value = "";
    }
  };

  return (
    <div style={{ padding: "40px", maxWidth: "600px", margin: "auto" }}>
      <h1>Simple RAG Chat Interface</h1>
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask a question about your documents"
        style={{ width: "100%", height: "100px", marginBottom: "10px" }}
      />
      <button onClick={askQuestion} disabled={loading}>
        {loading ? "Thinking" : "Ask Bot"}
      </button>
      <div>
        <input
          type="file"
          multiple
          accept=".pdf,.txt"
          onChange={handleUpload}
          disabled={ingesting}
        />
        {ingesting && <p>Processing... please wait</p>}
      </div>
      {answer && (
        <div style={{ marginTop: "20px" }}>
          <strong>AI Answer:</strong>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}
export default App;
