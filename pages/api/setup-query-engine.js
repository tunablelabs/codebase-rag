import { execFile } from "child_process";
import path from "path";

export default async function handler(req, res) {
    if (req.method !== "POST") {
        return res.status(405).json({ message: "Method not allowed" });
    }

    const { githubUrl, question, system_prompt, ast_bool} = req.body;
    if (!githubUrl || !question) {
        return res.status(400).json({ message: "Missing parameters" });
    }
    
    const scriptPath = path.resolve("./scripts/query_engine.py");
    execFile("python3", [scriptPath, githubUrl, question, system_prompt,ast_bool], (error, stdout, stderr) => {
        if (error) {
            console.error("Error executing Python script:", stderr || error.message);
            return res.status(500).json({ message: "Internal Server Error", error: stderr || error.message });
        }

        try {
            console.log(stdout)
            const response = JSON.parse(stdout);
            return res.status(200).json(response);
        } catch (parseError) {
            console.error("Error parsing JSON:", parseError, "Raw output:", stdout);
            return res.status(500).json({ message: "Invalid JSON from Python script", rawOutput: stdout });
        }
    });
}
