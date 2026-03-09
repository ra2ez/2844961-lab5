const express = require('express');
const app = express();
const PORT = 3000;

// Ensure Content-Type: application/json on ALL responses
app.use((req, res, next) => {
    res.setHeader('Content-Type', 'application/json');
    next();
});

app.use(express.json());

let books = [];

// ─── GET /whoami ────────────────────────────────────────────────────────────
// Test: "GET /whoami returns studentNumber" (10pts)
app.get('/whoami', (req, res) => {
    res.status(200).json({ studentNumber: "2844961" });
});

// ─── GET /books ─────────────────────────────────────────────────────────────
// Test: "GET /books returns empty array initially" (8pts)
app.get('/books', (req, res) => {
    res.status(200).json(books);
});

// ─── GET /books/:id ──────────────────────────────────────────────────────────
// Tests: "GET /books/:id returns created book" (8pts)
//        "GET /books/:id returns 404 for non-existent" (8pts)
app.get('/books/:id', (req, res) => {
    const book = books.find(b => b.id === req.params.id);
    if (!book) {
        return res.status(404).json({ error: "Book not found" });
    }
    res.status(200).json(book);
});

// ─── POST /books ─────────────────────────────────────────────────────────────
// Tests: "POST /books creates book (returns 201)" (12pts)
//        "POST /books with missing fields returns 400" (10pts)
app.post('/books', (req, res) => {
    const { id, title, details } = req.body || {};
    if (!id || !title) {
        return res.status(400).json({ error: "Missing required fields" });
    }
    const newBook = {
        id: String(id),
        title: String(title),
        details: Array.isArray(details) ? details : []
    };
    books.push(newBook);
    res.status(201).json(newBook);
});

// ─── PUT /books/:id ──────────────────────────────────────────────────────────
// Test: "PUT /books/:id updates book" (8pts)
app.put('/books/:id', (req, res) => {
    const bookIndex = books.findIndex(b => b.id === req.params.id);
    if (bookIndex === -1) {
        return res.status(404).json({ error: "Book not found" });
    }
    if (!req.body || !req.body.title) {
        return res.status(400).json({ error: "Missing required fields" });
    }
    books[bookIndex] = { ...books[bookIndex], ...req.body };
    res.status(200).json(books[bookIndex]);
});

// ─── DELETE /books/:id ───────────────────────────────────────────────────────
// Test: "DELETE /books/:id removes book" (8pts)
app.delete('/books/:id', (req, res) => {
    const bookIndex = books.findIndex(b => b.id === req.params.id);
    if (bookIndex === -1) {
        return res.status(404).json({ error: "Book not found" });
    }
    const deleted = books.splice(bookIndex, 1)[0];
    res.status(200).json(deleted);
});

// ─── POST /books/:id/details ─────────────────────────────────────────────────
// Test: "POST /books/:id/details adds detail" (8pts)
app.post('/books/:id/details', (req, res) => {
    const book = books.find(b => b.id === req.params.id);
    if (!book) {
        return res.status(404).json({ error: "Book not found" });
    }
    book.details.push(req.body);
    res.status(201).json(book);
});

// ─── DELETE /books/:id/details/:detailId ─────────────────────────────────────
// Test: "DELETE /books/:id/details/:detailId removes detail" (8pts)
app.delete('/books/:id/details/:detailId', (req, res) => {
    const book = books.find(b => b.id === req.params.id);
    if (!book) {
        return res.status(404).json({ error: "Book or detail not found" });
    }
    const detailIndex = book.details.findIndex(d => d.id === req.params.detailId);
    if (detailIndex === -1) {
        return res.status(404).json({ error: "Book or detail not found" });
    }
    const deleted = book.details.splice(detailIndex, 1)[0];
    res.status(200).json(deleted);
});

// ─── Global error handler (malformed JSON, unexpected errors) ────────────────
// Ensures Content-Type: application/json is always set even on errors
app.use((err, req, res, next) => {
    res.setHeader('Content-Type', 'application/json');
    if (err.type === 'entity.parse.failed') {
        return res.status(400).json({ error: "Invalid JSON" });
    }
    res.status(500).json({ error: "Internal server error" });
});

// ─── Start server ────────────────────────────────────────────────────────────
// Test: "Server starts on port 3000" (5pts)
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
