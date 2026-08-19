import express from 'express';
import { puter } from '@heyputer/puter.js';

const app = express();
app.use(express.json());

// Model – choose one from the list (they are free)
const MODEL = 'gemini-3.7-flash'; // or 'gemini-3.1-pro-preview', etc.

// ---------- Generate a new script ----------
app.post('/generate', async (req, res) => {
    const { instruction } = req.body;
    if (!instruction) {
        return res.status(400).json({ error: 'Missing instruction' });
    }

    try {
        const prompt = `You are an expert Python developer. Write a new Python script based on the user's request. Output ONLY the Python code, no explanations, no markdown formatting.\n\nUser request: ${instruction}`;
        const response = await puter.ai.chat(prompt, { model: MODEL });
        // Remove markdown fences if present
        let code = response.text || response;
        code = code.replace(/```python\n?/g, '').replace(/```\n?/g, '').trim();
        res.json({ code });
    } catch (err) {
        console.error('Generate error:', err);
        res.status(500).json({ error: err.message });
    }
});

// ---------- Edit an existing script ----------
app.post('/edit', async (req, res) => {
    const { original_script, instruction } = req.body;
    if (!original_script || !instruction) {
        return res.status(400).json({ error: 'Missing original_script or instruction' });
    }

    try {
        const prompt = `You are an expert Python developer. Modify the given script according to the user's instruction. Output ONLY the full, updated Python code, no extra text.\n\nOriginal script:\n\`\`\`python\n${original_script}\n\`\`\`\n\nInstruction: ${instruction}`;
        const response = await puter.ai.chat(prompt, { model: MODEL });
        let code = response.text || response;
        code = code.replace(/```python\n?/g, '').replace(/```\n?/g, '').trim();
        res.json({ code });
    } catch (err) {
        console.error('Edit error:', err);
        res.status(500).json({ error: err.message });
    }
});

// ---------- General question ----------
app.post('/ask', async (req, res) => {
    const { question } = req.body;
    if (!question) {
        return res.status(400).json({ error: 'Missing question' });
    }

    try {
        const response = await puter.ai.chat(question, { model: MODEL });
        const answer = response.text || response;
        res.json({ answer });
    } catch (err) {
        console.error('Ask error:', err);
        res.status(500).json({ error: err.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`AI Server running on port ${PORT}`);
});
