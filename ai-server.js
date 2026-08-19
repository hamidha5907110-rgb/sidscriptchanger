import express from 'express';
import { puter } from '@heyputer/puter.js';

const app = express();
app.use(express.json());

const MODEL = 'gemini-3.7-flash';

app.post('/generate', async (req, res) => {
    const { instruction } = req.body;
    if (!instruction) return res.status(400).json({ error: 'Missing instruction' });
    try {
        const prompt = `You are an expert Python developer. Write a new Python script based on the user's request. Output ONLY the Python code, no explanations, no markdown formatting.\n\nUser request: ${instruction}`;
        const response = await puter.ai.chat(prompt, { model: MODEL });
        let code = response.text || response;
        code = code.replace(/```python\n?/g, '').replace(/```\n?/g, '').trim();
        res.json({ code });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/edit', async (req, res) => {
    const { original_script, instruction } = req.body;
    if (!original_script || !instruction) return res.status(400).json({ error: 'Missing data' });
    try {
        const prompt = `You are an expert Python developer. Modify the given script according to the user's instruction. Output ONLY the full, updated Python code, no extra text.\n\nOriginal script:\n\`\`\`python\n${original_script}\n\`\`\`\n\nInstruction: ${instruction}`;
        const response = await puter.ai.chat(prompt, { model: MODEL });
        let code = response.text || response;
        code = code.replace(/```python\n?/g, '').replace(/```\n?/g, '').trim();
        res.json({ code });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/ask', async (req, res) => {
    const { question } = req.body;
    if (!question) return res.status(400).json({ error: 'Missing question' });
    try {
        const response = await puter.ai.chat(question, { model: MODEL });
        const answer = response.text || response;
        res.json({ answer });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`AI Server running on port ${PORT}`));
