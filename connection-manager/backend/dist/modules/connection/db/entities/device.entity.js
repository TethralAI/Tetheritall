var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Column, CreateDateColumn, Entity, Index, PrimaryColumn } from 'typeorm';
let DeviceEntity = class DeviceEntity {
    id;
    capabilities;
    status;
    createdAt;
};
__decorate([
    PrimaryColumn({ type: 'varchar', length: 128 }),
    __metadata("design:type", String)
], DeviceEntity.prototype, "id", void 0);
__decorate([
    Column({ type: 'jsonb', default: () => "'[]'::jsonb" }),
    __metadata("design:type", Array)
], DeviceEntity.prototype, "capabilities", void 0);
__decorate([
    Column({ type: 'varchar', length: 16, default: 'offline' }),
    Index(),
    __metadata("design:type", String)
], DeviceEntity.prototype, "status", void 0);
__decorate([
    CreateDateColumn({ type: 'timestamptz' }),
    __metadata("design:type", Date)
], DeviceEntity.prototype, "createdAt", void 0);
DeviceEntity = __decorate([
    Entity({ name: 'device' })
], DeviceEntity);
export { DeviceEntity };
//# sourceMappingURL=device.entity.js.map