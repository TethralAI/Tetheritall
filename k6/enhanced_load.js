import http from 'k6/http';
import { sleep, check, group, Rate, Trend, Counter } from 'k6';
import { SharedArray } from 'k6/data';

// Configuration
const GATEWAY = __ENV.GATEWAY_BASE || 'http://localhost:8000';
const API_KEY = __ENV.API_TOKEN || 'test-api-key';
const TEST_DURATION = __ENV.TEST_DURATION || '10m';
const VUS = __ENV.VUS || 50;
const RAMP_UP_TIME = __ENV.RAMP_UP_TIME || '2m';
const RAMP_DOWN_TIME = __ENV.RAMP_DOWN_TIME || '2m';

// Test data
const testDevices = new SharedArray('devices', function () {
    return [
        { provider: 'hue', external_id: 'hue:bridge1:light1' },
        { provider: 'hue', external_id: 'hue:bridge1:light2' },
        { provider: 'smartthings', external_id: 'st:device1' },
        { provider: 'smartthings', external_id: 'st:device2' },
        { provider: 'tuya', external_id: 'tuya:device1' },
        { provider: 'tuya', external_id: 'tuya:device2' },
    ];
});

const testUsers = new SharedArray('users', function () {
    return Array.from({ length: 100 }, (_, i) => ({
        id: `user${i}`,
        api_key: API_KEY,
        org_id: `org${Math.floor(i / 10)}`
    }));
});

// Metrics
const successRate = new Rate('success_rate');
const failureRate = new Rate('failure_rate');
const requestDuration = new Trend('request_duration');
const concurrentRequests = new Counter('concurrent_requests');
const cacheHitRate = new Rate('cache_hit_rate');
const rateLimitHits = new Counter('rate_limit_hits');

// Test scenarios
export const options = {
    scenarios: {
        // Scenario 1: Constant load
        constant_load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: RAMP_UP_TIME, target: VUS },
                { duration: TEST_DURATION, target: VUS },
                { duration: RAMP_DOWN_TIME, target: 0 },
            ],
            exec: 'constantLoad',
        },
        
        // Scenario 2: Spike testing
        spike_test: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '1m', target: 10 },
                { duration: '30s', target: 100 }, // Spike
                { duration: '1m', target: 100 },
                { duration: '30s', target: 10 },
                { duration: '1m', target: 10 },
            ],
            exec: 'spikeLoad',
        },
        
        // Scenario 3: Stress testing
        stress_test: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 20 },
                { duration: '5m', target: 20 },
                { duration: '2m', target: 40 },
                { duration: '5m', target: 40 },
                { duration: '2m', target: 60 },
                { duration: '5m', target: 60 },
                { duration: '2m', target: 0 },
            ],
            exec: 'stressLoad',
        },
        
        // Scenario 4: Complex operations
        complex_operations: {
            executor: 'constant-vus',
            vus: 10,
            duration: '5m',
            exec: 'complexOperations',
        },
        
        // Scenario 5: Simultaneous calls
        simultaneous_calls: {
            executor: 'constant-vus',
            vus: 20,
            duration: '5m',
            exec: 'simultaneousCalls',
        },
    },
    
    thresholds: {
        // Performance thresholds
        'http_req_duration': ['p(95)<500', 'p(99)<1000'],
        'http_req_failed': ['rate<0.01'],
        'success_rate': ['rate>0.95'],
        'failure_rate': ['rate<0.05'],
        'request_duration': ['p(95)<500'],
        
        // Rate limiting thresholds
        'rate_limit_hits': ['count<100'],
        
        // Cache performance
        'cache_hit_rate': ['rate>0.8'],
    },
};

// Common headers
const getHeaders = (user = null) => {
    const headers = {
        'x-api-key': user?.api_key || API_KEY,
        'content-type': 'application/json',
        'user-agent': 'k6-load-test',
    };
    
    if (user?.org_id) {
        headers['x-org-id'] = user.org_id;
    }
    
    return headers;
};

// Helper function to make requests with metrics
const makeRequest = (method, url, payload = null, headers = {}) => {
    const startTime = Date.now();
    concurrentRequests.add(1);
    
    const params = {
        headers: { ...getHeaders(), ...headers },
        timeout: '30s',
    };
    
    let response;
    if (method === 'GET') {
        response = http.get(url, params);
    } else if (method === 'POST') {
        response = http.post(url, payload, params);
    } else if (method === 'PUT') {
        response = http.put(url, payload, params);
    } else if (method === 'DELETE') {
        response = http.delete(url, params);
    }
    
    const duration = Date.now() - startTime;
    requestDuration.add(duration);
    concurrentRequests.add(-1);
    
    // Check for rate limiting
    if (response.status === 429) {
        rateLimitHits.add(1);
        failureRate.add(1);
        successRate.add(0);
    } else if (response.status >= 200 && response.status < 300) {
        successRate.add(1);
        failureRate.add(0);
    } else {
        successRate.add(0);
        failureRate.add(1);
    }
    
    return response;
};

// Test scenarios
export function constantLoad() {
    const user = testUsers[Math.floor(Math.random() * testUsers.length)];
    const device = testDevices[Math.floor(Math.random() * testDevices.length)];
    
    group('Constant Load Test', function () {
        // Health check
        const healthResponse = makeRequest('GET', `${GATEWAY}/health`);
        check(healthResponse, {
            'health check successful': (r) => r.status === 200,
        });
        
        // Device status
        const statusResponse = makeRequest('GET', `${GATEWAY}/tasks/status`);
        check(statusResponse, {
            'status check successful': (r) => r.status === 200,
        });
        
        // Capability operations
        const capabilityResponse = makeRequest(
            'POST',
            `${GATEWAY}/capability/${device.provider}/${device.external_id}/switch/on`,
            '{}',
            { 'Idempotency-Key': `k6-${Date.now()}-${Math.random()}` }
        );
        check(capabilityResponse, {
            'capability operation successful': (r) => r.status < 500,
        });
        
        // Cache test
        const cacheResponse = makeRequest('GET', `${GATEWAY}/mapping/suggestions`);
        check(cacheResponse, {
            'cache operation successful': (r) => r.status === 200,
        });
        
        sleep(Math.random() * 2 + 1); // Random sleep between 1-3 seconds
    });
}

export function spikeLoad() {
    const user = testUsers[Math.floor(Math.random() * testUsers.length)];
    
    group('Spike Load Test', function () {
        // Rapid fire requests during spike
        const requests = [];
        for (let i = 0; i < 5; i++) {
            const device = testDevices[Math.floor(Math.random() * testDevices.length)];
            requests.push(
                makeRequest(
                    'POST',
                    `${GATEWAY}/capability/${device.provider}/${device.external_id}/switch/on`,
                    '{}',
                    { 'Idempotency-Key': `spike-${Date.now()}-${i}` }
                )
            );
        }
        
        // Check all requests
        requests.forEach((response, index) => {
            check(response, {
                [`spike request ${index} successful`]: (r) => r.status < 500,
            });
        });
        
        sleep(0.1); // Very short sleep for spike testing
    });
}

export function stressLoad() {
    const user = testUsers[Math.floor(Math.random() * testUsers.length)];
    
    group('Stress Load Test', function () {
        // Heavy operations
        const device = testDevices[Math.floor(Math.random() * testDevices.length)];
        
        // Complex device operation
        const complexResponse = makeRequest(
            'POST',
            `${GATEWAY}/capability/${device.provider}/${device.external_id}/color/hsv`,
            JSON.stringify({ h: 120, s: 100, v: 50 }),
            { 'Idempotency-Key': `stress-${Date.now()}` }
        );
        check(complexResponse, {
            'complex operation successful': (r) => r.status < 500,
        });
        
        // Multiple simultaneous operations
        const operations = [
            { method: 'POST', path: `/capability/${device.provider}/${device.external_id}/switch/on`, payload: '{}' },
            { method: 'POST', path: `/capability/${device.provider}/${device.external_id}/dimmer/set`, payload: JSON.stringify({ level: 50 }) },
            { method: 'GET', path: `/tasks/status`, payload: null },
        ];
        
        const responses = operations.map(op => 
            makeRequest(
                op.method,
                `${GATEWAY}${op.path}`,
                op.payload,
                { 'Idempotency-Key': `stress-${Date.now()}-${Math.random()}` }
            )
        );
        
        responses.forEach((response, index) => {
            check(response, {
                [`stress operation ${index} successful`]: (r) => r.status < 500,
            });
        });
        
        sleep(Math.random() * 3 + 2); // Random sleep between 2-5 seconds
    });
}

export function complexOperations() {
    const user = testUsers[Math.floor(Math.random() * testUsers.length)];
    
    group('Complex Operations Test', function () {
        // Device commissioning workflow
        const commissioningResponse = makeRequest(
            'POST',
            `${GATEWAY}/hue/discover-bridges`,
            JSON.stringify({ network_range: '192.168.1.0/24' })
        );
        check(commissioningResponse, {
            'commissioning discovery successful': (r) => r.status < 500,
        });
        
        // Bridge pairing
        const pairingResponse = makeRequest(
            'POST',
            `${GATEWAY}/hue/pair-bridge`,
            JSON.stringify({ bridge_ip: '192.168.1.100', app_name: 'k6-test' })
        );
        check(pairingResponse, {
            'bridge pairing successful': (r) => r.status < 500,
        });
        
        // Device discovery
        const discoveryResponse = makeRequest(
            'GET',
            `${GATEWAY}/hue/bridges/bridge1/devices`
        );
        check(discoveryResponse, {
            'device discovery successful': (r) => r.status < 500,
        });
        
        // Complex automation
        const automationResponse = makeRequest(
            'POST',
            `${GATEWAY}/automation/routines/generate_llm`,
            JSON.stringify({
                devices: testDevices.slice(0, 3),
                routine_type: 'morning',
                preferences: { energy_saving: true, comfort: true }
            })
        );
        check(automationResponse, {
            'automation generation successful': (r) => r.status < 500,
        });
        
        sleep(Math.random() * 5 + 3); // Random sleep between 3-8 seconds
    });
}

export function simultaneousCalls() {
    const user = testUsers[Math.floor(Math.random() * testUsers.length)];
    
    group('Simultaneous Calls Test', function () {
        // Create multiple simultaneous requests
        const promises = [];
        
        // Multiple device operations
        for (let i = 0; i < 10; i++) {
            const device = testDevices[Math.floor(Math.random() * testDevices.length)];
            const operation = Math.random() > 0.5 ? 'on' : 'off';
            
            promises.push(
                makeRequest(
                    'POST',
                    `${GATEWAY}/capability/${device.provider}/${device.external_id}/switch/${operation}`,
                    '{}',
                    { 'Idempotency-Key': `simultaneous-${Date.now()}-${i}` }
                )
            );
        }
        
        // Multiple status checks
        for (let i = 0; i < 5; i++) {
            promises.push(
                makeRequest('GET', `${GATEWAY}/health`),
                makeRequest('GET', `${GATEWAY}/tasks/status`),
                makeRequest('GET', `${GATEWAY}/mapping/suggestions`)
            );
        }
        
        // Wait for all requests to complete
        const responses = promises;
        
        // Check success rate
        const successfulRequests = responses.filter(r => r.status < 500).length;
        const successRate = successfulRequests / responses.length;
        
        check({ successRate }, {
            'simultaneous calls success rate > 90%': (r) => r.successRate > 0.9,
        });
        
        sleep(Math.random() * 2 + 1); // Random sleep between 1-3 seconds
    });
}

// Setup and teardown
export function setup() {
    console.log('Starting enhanced load test...');
    console.log(`Gateway: ${GATEWAY}`);
    console.log(`Test duration: ${TEST_DURATION}`);
    console.log(`Virtual users: ${VUS}`);
    
    // Warm up the system
    const warmupResponse = http.get(`${GATEWAY}/health`, {
        headers: getHeaders(),
        timeout: '30s',
    });
    
    check(warmupResponse, {
        'warmup successful': (r) => r.status === 200,
    });
    
    return { warmup: warmupResponse.status === 200 };
}

export function teardown(data) {
    console.log('Enhanced load test completed');
    console.log(`Warmup successful: ${data.warmup}`);
}

// Handle test completion
export function handleSummary(data) {
    console.log('Test Summary:');
    console.log(`Total requests: ${data.metrics.http_reqs.values.count}`);
    console.log(`Success rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}% failed`);
    console.log(`Average response time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
    console.log(`95th percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
    console.log(`99th percentile: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
    
    return {
        'enhanced-load-test-summary.json': JSON.stringify(data, null, 2),
    };
}
