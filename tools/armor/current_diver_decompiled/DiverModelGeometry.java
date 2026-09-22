/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  net.minecraft.client.model.HumanoidModel
 *  net.minecraft.client.model.geom.PartPose
 *  net.minecraft.client.model.geom.builders.CubeDeformation
 *  net.minecraft.client.model.geom.builders.CubeListBuilder
 *  net.minecraft.client.model.geom.builders.LayerDefinition
 *  net.minecraft.client.model.geom.builders.MeshDefinition
 *  net.minecraft.client.model.geom.builders.PartDefinition
 *  net.minecraft.world.entity.EquipmentSlot
 */
package ru.koshpack.forgebridge.armor.client;

import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.world.entity.EquipmentSlot;

final class DiverModelGeometry {
    private DiverModelGeometry() {
    }

    static LayerDefinition create(EquipmentSlot equipmentSlot, int n) {
        MeshDefinition meshDefinition = HumanoidModel.createMesh((CubeDeformation)new CubeDeformation(0.0f), (float)0.0f);
        PartDefinition partDefinition = meshDefinition.getRoot();
        PartDefinition partDefinition2 = partDefinition.addOrReplaceChild("head", CubeListBuilder.create(), PartPose.ZERO);
        partDefinition.addOrReplaceChild("hat", CubeListBuilder.create(), PartPose.ZERO);
        PartDefinition partDefinition3 = partDefinition.addOrReplaceChild("body", CubeListBuilder.create(), PartPose.ZERO);
        PartDefinition partDefinition4 = partDefinition.addOrReplaceChild("right_arm", CubeListBuilder.create(), PartPose.offset((float)-5.0f, (float)2.0f, (float)0.0f));
        PartDefinition partDefinition5 = partDefinition.addOrReplaceChild("left_arm", CubeListBuilder.create(), PartPose.offset((float)5.0f, (float)2.0f, (float)0.0f));
        PartDefinition partDefinition6 = partDefinition.addOrReplaceChild("right_leg", CubeListBuilder.create(), PartPose.offset((float)-1.9f, (float)12.0f, (float)0.0f));
        PartDefinition partDefinition7 = partDefinition.addOrReplaceChild("left_leg", CubeListBuilder.create(), PartPose.offset((float)1.9f, (float)12.0f, (float)0.0f));
        if (equipmentSlot == EquipmentSlot.HEAD) {
            DiverModelGeometry.addHead(partDefinition2, n);
        }
        if (equipmentSlot == EquipmentSlot.CHEST) {
            DiverModelGeometry.addChest(partDefinition3, partDefinition4, partDefinition5, n);
        }
        if (equipmentSlot == EquipmentSlot.LEGS) {
            DiverModelGeometry.addLegs(partDefinition3, partDefinition6, partDefinition7, n);
        }
        if (equipmentSlot == EquipmentSlot.FEET) {
            DiverModelGeometry.addBoots(partDefinition6, partDefinition7, n);
        }
        return LayerDefinition.create((MeshDefinition)meshDefinition, (int)64, (int)64);
    }

    private static CubeListBuilder box(int n, int n2, float f, float f2, float f3, float f4, float f5, float f6, float f7) {
        return CubeListBuilder.create().texOffs(n, n2).addBox(f, f2, f3, f4, f5, f6, new CubeDeformation(f7));
    }

    private static void addHead(PartDefinition partDefinition, int n) {
        partDefinition.addOrReplaceChild("helmet_shell", DiverModelGeometry.box(0, 0, -4.0f, -8.0f, -4.0f, 8.0f, 8.0f, 8.0f, 0.8f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("viewport_frame", DiverModelGeometry.box(0, 18, -3.5f, -6.8f, -4.96f, 7.0f, 5.2f, 0.45f, 0.0f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("viewport_left", DiverModelGeometry.box(18, 18, -3.0f, -6.35f, -5.24f, 2.7f, 4.25f, 0.18f, 0.0f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("viewport_right", DiverModelGeometry.box(32, 18, 0.3f, -6.35f, -5.24f, 2.7f, 4.25f, 0.18f, 0.0f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("viewport_bridge", DiverModelGeometry.box(46, 18, -0.3f, -6.55f, -5.28f, 0.6f, 4.65f, 0.24f, 0.0f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("rear_service_hatch", DiverModelGeometry.box(0, 26, -2.5f, -5.9f, 4.83f, 5.0f, 3.8f, 0.28f, 0.0f), PartPose.ZERO);
        if (n >= 2) {
            partDefinition.addOrReplaceChild("side_coupler_r", DiverModelGeometry.box(22, 26, -5.22f, -5.9f, -1.6f, 0.55f, 3.2f, 3.2f, 0.03f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("side_coupler_l", DiverModelGeometry.box(30, 26, 4.67f, -5.9f, -1.6f, 0.55f, 3.2f, 3.2f, 0.03f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("top_cap", DiverModelGeometry.box(38, 26, -2.45f, -9.1f, -2.55f, 4.9f, 0.55f, 5.1f, 0.02f), PartPose.ZERO);
        }
        if (n >= 3) {
            partDefinition.addOrReplaceChild("brow_guard", DiverModelGeometry.box(0, 34, -3.95f, -7.5f, -5.34f, 7.9f, 0.65f, 0.62f, 0.02f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("lamp_r", DiverModelGeometry.box(18, 34, -5.18f, -7.15f, -2.55f, 0.55f, 1.8f, 1.65f, 0.02f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("lamp_l", DiverModelGeometry.box(24, 34, 4.63f, -7.15f, -2.55f, 0.55f, 1.8f, 1.65f, 0.02f), PartPose.ZERO);
        }
        if (n >= 4) {
            partDefinition.addOrReplaceChild("top_handle_front", DiverModelGeometry.box(30, 34, -2.5f, -9.5f, -2.4f, 5.0f, 0.55f, 0.55f, 0.03f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("top_handle_back", DiverModelGeometry.box(40, 34, -2.5f, -9.5f, 1.85f, 5.0f, 0.55f, 0.55f, 0.03f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("top_handle_left", DiverModelGeometry.box(50, 34, -2.5f, -9.5f, -1.95f, 0.55f, 0.55f, 4.35f, 0.03f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("top_handle_right", DiverModelGeometry.box(56, 34, 1.95f, -9.5f, -1.95f, 0.55f, 0.55f, 4.35f, 0.03f), PartPose.ZERO);
        }
    }

    private static void addChest(PartDefinition partDefinition, PartDefinition partDefinition2, PartDefinition partDefinition3, int n) {
        partDefinition.addOrReplaceChild("body_shell", DiverModelGeometry.box(0, 0, -4.0f, 0.0f, -2.0f, 8.0f, 12.0f, 4.0f, 0.34f), PartPose.ZERO);
        partDefinition2.addOrReplaceChild("right_sleeve", DiverModelGeometry.box(24, 0, -3.0f, -2.0f, -2.0f, 4.0f, 12.0f, 4.0f, 0.28f), PartPose.ZERO);
        partDefinition3.addOrReplaceChild("left_sleeve", DiverModelGeometry.box(40, 0, -1.0f, -2.0f, -2.0f, 4.0f, 12.0f, 4.0f, 0.28f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("neck_lock", DiverModelGeometry.box(0, 20, -3.75f, -0.4f, -2.35f, 7.5f, 1.15f, 4.7f, 0.0f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("front_harness", DiverModelGeometry.box(26, 20, -3.15f, 1.1f, -2.48f, 6.3f, 7.2f, 0.24f, 0.0f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("air_tank", DiverModelGeometry.box(0, 30, -2.65f, 1.1f, 2.36f, 5.3f, 7.8f, 1.5f, 0.0f), PartPose.ZERO);
        partDefinition2.addOrReplaceChild("right_cuff", DiverModelGeometry.box(22, 30, -3.52f, 5.55f, -2.48f, 4.95f, 3.75f, 4.96f, 0.08f), PartPose.ZERO);
        partDefinition3.addOrReplaceChild("left_cuff", DiverModelGeometry.box(42, 30, -1.43f, 5.55f, -2.48f, 4.95f, 3.75f, 4.96f, 0.08f), PartPose.ZERO);
        if (n >= 2) {
            partDefinition2.addOrReplaceChild("right_shoulder_guard", DiverModelGeometry.box(0, 42, -3.52f, -2.55f, -2.52f, 5.04f, 1.3f, 5.04f, 0.04f), PartPose.ZERO);
            partDefinition3.addOrReplaceChild("left_shoulder_guard", DiverModelGeometry.box(20, 42, -1.52f, -2.55f, -2.52f, 5.04f, 1.3f, 5.04f, 0.04f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("regulator", DiverModelGeometry.box(40, 42, -1.2f, 2.05f, -2.92f, 2.4f, 2.35f, 0.58f, 0.03f), PartPose.ZERO);
        }
        if (n >= 3) {
            partDefinition.addOrReplaceChild("tank_left", DiverModelGeometry.box(0, 50, -3.78f, 1.3f, 2.4f, 1.9f, 6.8f, 1.62f, 0.02f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("tank_right", DiverModelGeometry.box(10, 50, 1.88f, 1.3f, 2.4f, 1.9f, 6.8f, 1.62f, 0.02f), PartPose.ZERO);
            partDefinition.addOrReplaceChild("chest_plate", DiverModelGeometry.box(20, 50, -3.08f, 1.75f, -2.92f, 6.16f, 5.55f, 0.58f, 0.02f), PartPose.ZERO);
        }
        if (n >= 4) {
            partDefinition.addOrReplaceChild("lower_weight_belt", DiverModelGeometry.box(44, 50, -4.02f, 8.2f, -2.78f, 8.04f, 1.95f, 5.56f, 0.04f), PartPose.ZERO);
        }
    }

    private static void addLegs(PartDefinition partDefinition, PartDefinition partDefinition2, PartDefinition partDefinition3, int n) {
        partDefinition.addOrReplaceChild("waist_shell", DiverModelGeometry.box(0, 0, -4.0f, 8.0f, -2.0f, 8.0f, 4.0f, 4.0f, 0.25f), PartPose.ZERO);
        partDefinition2.addOrReplaceChild("right_leg_shell", DiverModelGeometry.box(24, 0, -2.0f, 0.0f, -2.0f, 4.0f, 12.0f, 4.0f, 0.26f), PartPose.ZERO);
        partDefinition3.addOrReplaceChild("left_leg_shell", DiverModelGeometry.box(40, 0, -2.0f, 0.0f, -2.0f, 4.0f, 12.0f, 4.0f, 0.26f), PartPose.ZERO);
        partDefinition2.addOrReplaceChild("right_knee", DiverModelGeometry.box(0, 22, -2.2f, 4.15f, -2.38f, 4.4f, 2.1f, 0.38f, 0.0f), PartPose.ZERO);
        partDefinition3.addOrReplaceChild("left_knee", DiverModelGeometry.box(12, 22, -2.2f, 4.15f, -2.38f, 4.4f, 2.1f, 0.38f, 0.0f), PartPose.ZERO);
        if (n >= 2) {
            partDefinition2.addOrReplaceChild("right_thigh_weight", DiverModelGeometry.box(24, 22, -2.48f, 1.1f, 1.88f, 0.65f, 3.65f, 1.0f, 0.02f), PartPose.ZERO);
            partDefinition3.addOrReplaceChild("left_thigh_weight", DiverModelGeometry.box(30, 22, 1.83f, 1.1f, 1.88f, 0.65f, 3.65f, 1.0f, 0.02f), PartPose.ZERO);
        }
        if (n >= 3) {
            partDefinition2.addOrReplaceChild("right_shin_guard", DiverModelGeometry.box(36, 22, -2.38f, 6.05f, -2.6f, 4.76f, 3.85f, 0.62f, 0.02f), PartPose.ZERO);
            partDefinition3.addOrReplaceChild("left_shin_guard", DiverModelGeometry.box(50, 22, -2.38f, 6.05f, -2.6f, 4.76f, 3.85f, 0.62f, 0.02f), PartPose.ZERO);
        }
        if (n >= 4) {
            partDefinition.addOrReplaceChild("front_apron", DiverModelGeometry.box(0, 34, -2.92f, 8.2f, -2.8f, 5.84f, 4.15f, 0.58f, 0.03f), PartPose.ZERO);
        }
    }

    private static void addBoots(PartDefinition partDefinition, PartDefinition partDefinition2, int n) {
        partDefinition.addOrReplaceChild("right_boot", DiverModelGeometry.box(0, 0, -2.0f, 7.0f, -2.0f, 4.0f, 5.0f, 4.0f, 0.46f), PartPose.ZERO);
        partDefinition2.addOrReplaceChild("left_boot", DiverModelGeometry.box(20, 0, -2.0f, 7.0f, -2.0f, 4.0f, 5.0f, 4.0f, 0.46f), PartPose.ZERO);
        partDefinition.addOrReplaceChild("right_sole", DiverModelGeometry.box(40, 0, -2.45f, 11.1f, -2.58f, 4.9f, 0.72f, 5.15f, 0.0f), PartPose.ZERO);
        partDefinition2.addOrReplaceChild("left_sole", DiverModelGeometry.box(40, 8, -2.45f, 11.1f, -2.58f, 4.9f, 0.72f, 5.15f, 0.0f), PartPose.ZERO);
        if (n >= 2) {
            partDefinition.addOrReplaceChild("right_toe_weight", DiverModelGeometry.box(0, 16, -2.28f, 8.95f, -3.02f, 4.56f, 1.85f, 0.78f, 0.02f), PartPose.ZERO);
            partDefinition2.addOrReplaceChild("left_toe_weight", DiverModelGeometry.box(12, 16, -2.28f, 8.95f, -3.02f, 4.56f, 1.85f, 0.78f, 0.02f), PartPose.ZERO);
        }
        if (n >= 3) {
            partDefinition.addOrReplaceChild("right_ankle_band", DiverModelGeometry.box(24, 16, -2.46f, 6.82f, -2.46f, 4.92f, 1.05f, 4.92f, 0.03f), PartPose.ZERO);
            partDefinition2.addOrReplaceChild("left_ankle_band", DiverModelGeometry.box(42, 16, -2.46f, 6.82f, -2.46f, 4.92f, 1.05f, 4.92f, 0.03f), PartPose.ZERO);
        }
    }
}

