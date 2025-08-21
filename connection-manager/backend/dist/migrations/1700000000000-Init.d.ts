import { MigrationInterface, QueryRunner } from 'typeorm';
export declare class Init1700000000000 implements MigrationInterface {
    name: string;
    up(q: QueryRunner): Promise<void>;
    down(q: QueryRunner): Promise<void>;
}
