import { NextApiRequest, NextApiResponse } from "next";
import { execFile } from "child_process";
import path from "path";
import { promisify } from "util";

// Promisify execFile for better async/await handling
const execFileAsync = promisify(execFile);

type ApiResponse = {
  response?: string;
  error?: string;
  message?: string;
  rawOutput?: string;
};

/**
 * API handler for querying GitHub repositories.
 *
 * Request Body:
 * - githubUrl: URL of the GitHub repository.
 * - question: A question about the repository's code.
 *
 * Response:
 * - response: The answer to the query (if successful).
 * - error: Error message (if any).
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ApiResponse>
) {
  if (req.method !== "POST") {
    return res.status(405).json({ message: "Method not allowed" });
  }

  const { githubUrl, question }: { githubUrl?: string; question?: string } =
    req.body;

  // Validate input
  if (!githubUrl || !question) {
    return res
      .status(400)
      .json({ message: "Missing parameters: 'githubUrl' and 'question' are required." });
  }

  const scriptPath = path.resolve("./scripts/query_engine.py");
  console.log("Executing script at:", scriptPath);

  try {
    // Execute the Python script
    const { stdout, stderr } = await execFileAsync("python", [
      scriptPath,
      githubUrl,
      question,
    ]);

    if (stderr) {
      console.error("Python script error:", stderr);
      return res.status(500).json({
        message: "Internal Server Error while executing the Python script",
        error: stderr,
      });
    }

    try {
      // Parse the script output as JSON
      const response = JSON.parse(stdout);
      return res.status(200).json(response);
    } catch (parseError) {
      console.error(
        "Error parsing JSON:",
        parseError,
        "Raw output:",
        stdout
      );
      return res.status(500).json({
        message: "Invalid JSON response from Python script",
        rawOutput: stdout,
      });
    }
  } catch (error: any) {
    // Improved error handling with type guards
    console.error("Error executing Python script:", error);
    return res.status(500).json({
      message: "Failed to execute Python script",
      error: error.message || "An unknown error occurred",
    });
  }
}
