type CommissionStartDto = {
    ssid?: string;
    psk?: string;
    metadata?: Record<string, unknown>;
};
export declare class CommissioningController {
    private sessions;
    start(_body: CommissionStartDto): {
        id: string;
    };
    status(id: string): {
        id: string;
        status: string;
    };
}
export {};
