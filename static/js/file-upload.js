/**
 * FileUploader — chunked upload with retry and progress callbacks.
 *
 * Usage:
 *   const uploader = new FileUploader({ chunkUrl, finalizeUrl, csrfToken, onProgress });
 *   await uploader.upload(file, { title, description, folder_id });
 */
class FileUploader {
    constructor(options = {}) {
        this.chunkUrl    = options.chunkUrl;
        this.finalizeUrl = options.finalizeUrl;
        this.csrfToken   = options.csrfToken;
        this.chunkSize   = options.chunkSize || 5 * 1024 * 1024;  // 5 MB default
        this.maxRetries  = options.maxRetries || 3;
        this._onProgress = options.onProgress || function() {};
    }

    /**
     * Upload a single File object in chunks, then finalize.
     * @param {File} file
     * @param {Object} metadata  { title, description, folder_id }
     * @returns {Object} server response from finalize
     */
    async upload(file, metadata = {}) {
        const uploadId    = this._generateId();
        const totalChunks = Math.ceil(file.size / this.chunkSize);

        for (let i = 0; i < totalChunks; i++) {
            const start = i * this.chunkSize;
            const chunk = file.slice(start, start + this.chunkSize);

            await this._sendChunk(chunk, {
                upload_id:    uploadId,
                chunk_index:  i,
                total_chunks: totalChunks,
                file_name:    file.name,
                file_size:    file.size,
            });

            const pct = Math.round(((i + 1) / totalChunks) * 100);
            this._onProgress(pct, file.name);
        }

        return this._finalize(uploadId, { ...metadata, file_name: file.name });
    }

    // ---------------------------------------------------------------- //

    async _sendChunk(chunkBlob, meta) {
        return this._withRetry(async () => {
            const form = new FormData();
            form.append('chunk', chunkBlob);
            Object.entries(meta).forEach(([k, v]) => form.append(k, String(v)));

            const resp = await fetch(this.chunkUrl, {
                method:  'POST',
                headers: { 'X-CSRFToken': this.csrfToken },
                body:    form,
            });

            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                throw new Error(data.error || `Chunk upload failed (HTTP ${resp.status})`);
            }
            return resp.json();
        });
    }

    async _finalize(uploadId, metadata) {
        const payload = { upload_id: uploadId, ...metadata };

        const resp = await fetch(this.finalizeUrl, {
            method:  'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  this.csrfToken,
            },
            body: JSON.stringify(payload),
        });

        const data = await resp.json().catch(() => ({}));

        if (!resp.ok) {
            const msg = data.error || `Finalize failed (HTTP ${resp.status})`;
            const err = new Error(msg);
            if (data.quota_exceeded) err.quotaExceeded = true;
            throw err;
        }

        return data;
    }

    async _withRetry(fn) {
        let lastErr;
        for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
                return await fn();
            } catch (err) {
                lastErr = err;
                if (attempt < this.maxRetries - 1) {
                    await this._sleep(1000 * Math.pow(2, attempt));
                }
            }
        }
        throw lastErr;
    }

    _generateId() {
        return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 9);
    }

    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
