addEventListener('fetch', event => {
    event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
    const url = new URL(request.url)
    const data = url.searchParams.get('data')
    const filename = url.searchParams.get('filename')

    // Handle OPTIONS preflight request
    if (request.method === 'OPTIONS') {
        return new Response(null, {
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                'Access-Control-Allow-Headers': 'Range, Content-Type, User-Agent',
                'Access-Control-Max-Age': '86400',
            },
            status: 204
        })
    }

    if (!data) {
        return new Response('Missing data parameter', {
            status: 400,
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'text/plain'
            }
        })
    }

    try {
        // Decode the base64 URL
        const padding = (4 - (data.length % 4)) % 4
        const paddedData = data + '='.repeat(padding)
        const decodedUrl = atob(paddedData.replace(/-/g, '+').replace(/_/g, '/'))

        console.log('Fetching from:', decodedUrl)

        // Forward range header if present
        const headers = {
            'User-Agent': request.headers.get('User-Agent') || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        if (request.headers.get('Range')) {
            headers['Range'] = request.headers.get('Range')
        }

        // Fetch from Debrid-Link
        const response = await fetch(decodedUrl, { headers })

        // Create new response with CORS headers
        const newHeaders = new Headers(response.headers)

        // Add CORS headers for video streaming
        newHeaders.set('Access-Control-Allow-Origin', '*')
        newHeaders.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        newHeaders.set('Access-Control-Allow-Headers', 'Range, Content-Type, User-Agent')
        newHeaders.set('Access-Control-Expose-Headers', 'Content-Length, Content-Range, Accept-Ranges, Content-Type')

        // Set Content-Disposition if filename provided
        if (filename) {
            newHeaders.set('Content-Disposition', `inline; filename="${filename}"`)
        }

        // Ensure Accept-Ranges header is present for video seeking
        if (!newHeaders.has('Accept-Ranges')) {
            newHeaders.set('Accept-Ranges', 'bytes')
        }

        return new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: newHeaders
        })

    } catch (error) {
        console.error('Worker error:', error)
        return new Response('Error proxying request: ' + error.message, {
            status: 500,
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'text/plain'
            }
        })
    }
}
