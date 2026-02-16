/**
 * Cloudflare Worker - Debrid-Link Proxy
 * 
 * This worker acts as a proxy between users and Debrid-Link,
 * ensuring all requests come from a single IP (Cloudflare's).
 * 
 * Benefits:
 * - Prevents account bans from multiple user IPs
 * - Hides actual Debrid-Link URLs from users
 * - Free tier: 100,000 requests/day
 */

addEventListener('fetch', event => {
    event.respondWith(handleRequest(event.request))
})

/**
 * Main request handler
 */
async function handleRequest(request) {
    const url = new URL(request.url)

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
        return handleCORS()
    }

    // Only allow GET requests to /download endpoint
    if (url.pathname !== '/download' || request.method !== 'GET') {
        return new Response('Not Found', { status: 404 })
    }

    try {
        // Get encrypted data and filename from query params
        const data = url.searchParams.get('data')
        const filename = url.searchParams.get('filename')

        if (!data) {
            return new Response('Missing data parameter', { status: 400 })
        }

        // Decode the URL (base64 + URL-safe decoding)
        const decodedUrl = decodeData(data)

        if (!decodedUrl || !decodedUrl.startsWith('http')) {
            return new Response('Invalid data parameter', { status: 400 })
        }

        // Get Range header from incoming request for resume support
        const rangeHeader = request.headers.get('Range')

        // Prepare headers for upstream request
        const upstreamHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        // Forward Range header if present (for resume support)
        if (rangeHeader) {
            upstreamHeaders['Range'] = rangeHeader
        }

        // Fetch the file from Debrid-Link with Range support
        const response = await fetch(decodedUrl, {
            method: 'GET',
            headers: upstreamHeaders,
        })

        if (!response.ok) {
            return new Response(`Upstream error: ${response.status}`, { status: response.status })
        }

        // Stream the response back to the user with proper headers
        const headers = new Headers(response.headers)

        // Override/add important headers
        if (filename) {
            headers.set('Content-Disposition', `attachment; filename="${filename}"`)
        }
        headers.set('Access-Control-Allow-Origin', '*')

        // Keep original Cache-Control or set default
        if (!headers.has('Cache-Control')) {
            headers.set('Cache-Control', 'public, max-age=3600')
        }

        // Ensure range-related headers are preserved
        // These are critical for resume functionality:
        // - Accept-Ranges: indicates server supports range requests
        // - Content-Range: specifies which part of the resource is being sent
        // - Content-Length: size of the response (partial or full)

        // Return with appropriate status code (206 for partial content, 200 for full)
        return new Response(response.body, {
            status: response.status, // Preserve 206 Partial Content or 200 OK
            headers: headers,
        })

    } catch (error) {
        console.error('Worker error:', error)
        return new Response(`Internal error: ${error.message}`, { status: 500 })
    }
}

/**
 * Decode the encrypted data parameter
 * The data is base64-encoded (with URL-safe characters)
 */
function decodeData(data) {
    try {
        // URL-safe base64 decoding
        // Replace URL-safe characters back to standard base64
        const base64 = data.replace(/-/g, '+').replace(/_/g, '/')

        // Decode from base64
        const decoded = atob(base64)

        return decoded

    } catch (error) {
        console.error('Decode error:', error)
        return null
    }
}

/**
 * Handle CORS preflight requests
 */
function handleCORS() {
    return new Response(null, {
        status: 204,
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Range',
            'Access-Control-Max-Age': '86400',
        },
    })
}
