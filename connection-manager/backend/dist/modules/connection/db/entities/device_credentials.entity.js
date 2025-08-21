var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';
let DeviceCredentialsEntity = class DeviceCredentialsEntity {
    id;
    deviceId;
    encBlob;
    encAlg;
    keyRef;
    createdAt;
    updatedAt;
};
__decorate([
    PrimaryGeneratedColumn('uuid'),
    __metadata("design:type", String)
], DeviceCredentialsEntity.prototype, "id", void 0);
__decorate([
    Column({ type: 'varchar', length: 128 }),
    Index(),
    __metadata("design:type", String)
], DeviceCredentialsEntity.prototype, "deviceId", void 0);
__decorate([
    Column({ type: 'bytea' }),
    __metadata("design:type", Buffer)
], DeviceCredentialsEntity.prototype, "encBlob", void 0);
__decorate([
    Column({ type: 'varchar', length: 64 }),
    __metadata("design:type", String)
], DeviceCredentialsEntity.prototype, "encAlg", void 0);
__decorate([
    Column({ type: 'varchar', length: 256 }),
    __metadata("design:type", String)
], DeviceCredentialsEntity.prototype, "keyRef", void 0);
__decorate([
    CreateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], DeviceCredentialsEntity.prototype, "createdAt", void 0);
__decorate([
    UpdateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], DeviceCredentialsEntity.prototype, "updatedAt", void 0);
DeviceCredentialsEntity = __decorate([
    Entity({ name: 'device_credentials' })
], DeviceCredentialsEntity);
export { DeviceCredentialsEntity };
//# sourceMappingURL=device_credentials.entity.js.map