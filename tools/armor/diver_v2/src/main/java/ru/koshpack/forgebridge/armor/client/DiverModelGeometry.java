package ru.koshpack.forgebridge.armor.client;

import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.world.entity.EquipmentSlot;

/**
 * KoshPack donor-based Diver progression.
 *
 * Geometry direction is adapted from the Public Domain "Scuba Diving Suit"
 * model set. It is deliberately reworked into four KoshPack progression tiers:
 * I improvised -> II equipped -> III professional SCUBA -> IV deep-sea elite.
 */
final class DiverModelGeometry {
    private DiverModelGeometry() {}

    static LayerDefinition create(EquipmentSlot slot, int tier) {
        MeshDefinition mesh = HumanoidModel.createMesh(new CubeDeformation(0.0F), 0.0F);
        PartDefinition root = mesh.getRoot();

        PartDefinition head = root.addOrReplaceChild(
                "head", CubeListBuilder.create(), PartPose.ZERO);
        root.addOrReplaceChild("hat", CubeListBuilder.create(), PartPose.ZERO);

        PartDefinition body = root.addOrReplaceChild(
                "body", CubeListBuilder.create(), PartPose.ZERO);
        PartDefinition rightArm = root.addOrReplaceChild(
                "right_arm", CubeListBuilder.create(), PartPose.offset(-5.0F, 2.0F, 0.0F));
        PartDefinition leftArm = root.addOrReplaceChild(
                "left_arm", CubeListBuilder.create(), PartPose.offset(5.0F, 2.0F, 0.0F));
        PartDefinition rightLeg = root.addOrReplaceChild(
                "right_leg", CubeListBuilder.create(), PartPose.offset(-1.9F, 12.0F, 0.0F));
        PartDefinition leftLeg = root.addOrReplaceChild(
                "left_leg", CubeListBuilder.create(), PartPose.offset(1.9F, 12.0F, 0.0F));

        int t = Math.max(1, Math.min(4, tier));
        if (slot == EquipmentSlot.HEAD) {
            addHead(head, t);
        } else if (slot == EquipmentSlot.CHEST) {
            addChest(body, rightArm, leftArm, t);
        } else if (slot == EquipmentSlot.LEGS) {
            addLegs(body, rightLeg, leftLeg, t);
        } else if (slot == EquipmentSlot.FEET) {
            addBoots(rightLeg, leftLeg, t);
        }

        return LayerDefinition.create(mesh, 64, 64);
    }

    private static CubeListBuilder box(
            int u, int v,
            float x, float y, float z,
            float dx, float dy, float dz,
            float inflate) {
        return CubeListBuilder.create()
                .texOffs(u, v)
                .addBox(x, y, z, dx, dy, dz, new CubeDeformation(inflate));
    }

    private static CubeListBuilder mirroredBox(
            int u, int v,
            float x, float y, float z,
            float dx, float dy, float dz,
            float inflate) {
        return CubeListBuilder.create()
                .texOffs(u, v)
                .mirror()
                .addBox(x, y, z, dx, dy, dz, new CubeDeformation(inflate))
                .mirror(false);
    }

    private static void addHead(PartDefinition head, int tier) {
        if (tier == 1) {
            // Poor improvised diver: cloth cap + cheap rectangular mask + one snorkel.
            head.addOrReplaceChild(
                    "patched_hood_i",
                    box(0, 0, -4.0F, -8.15F, -4.0F, 8.0F, 7.4F, 8.0F, 0.16F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "cheap_mask_frame_i",
                    box(0, 18, -3.25F, -6.45F, -4.72F, 6.5F, 3.35F, 0.42F, 0.0F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "cheap_glass_i",
                    box(48, 0, -2.75F, -6.02F, -4.91F, 5.5F, 2.25F, 0.14F, 0.0F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "snorkel_pipe_i",
                    box(32, 0, 3.85F, -7.85F, -3.15F, 0.52F, 6.5F, 0.52F, 0.02F),
                    PartPose.rotation(0.0F, 0.0F, -0.08F));
            head.addOrReplaceChild(
                    "snorkel_top_i",
                    box(32, 8, 3.65F, -8.55F, -3.12F, 1.25F, 0.55F, 0.55F, 0.02F),
                    PartPose.ZERO);
            return;
        }

        if (tier == 2) {
            // Proper recreational scuba hood and mask.
            head.addOrReplaceChild(
                    "scuba_hood_ii",
                    box(0, 0, -4.0F, -8.35F, -4.0F, 8.0F, 8.0F, 8.0F, 0.36F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "mask_frame_ii",
                    box(0, 18, -3.45F, -6.65F, -4.86F, 6.9F, 4.15F, 0.46F, 0.0F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "mask_glass_ii",
                    box(48, 0, -2.98F, -6.18F, -5.08F, 5.96F, 3.05F, 0.16F, 0.0F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "regulator_mouth_ii",
                    box(32, 10, -1.45F, -3.22F, -5.05F, 2.9F, 1.45F, 0.72F, 0.0F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "side_hose_pin_ii",
                    box(38, 10, 4.48F, -4.85F, -1.28F, 0.72F, 2.25F, 2.56F, 0.04F),
                    PartPose.ZERO);
            return;
        }

        if (tier == 3) {
            // Professional SCUBA: based on the donor's inflated shell + mask + hose couplers.
            head.addOrReplaceChild(
                    "scuba_shell_iii",
                    box(0, 0, -4.0F, -8.5F, -4.0F, 8.0F, 8.0F, 8.0F, 0.75F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "scuba_outer_iii",
                    box(0, 0, -4.0F, -8.25F, -4.0F, 8.0F, 8.0F, 8.0F, 1.02F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "pro_mask_frame_iii",
                    box(11, 35, -3.15F, -6.75F, -5.18F, 6.3F, 4.3F, 0.58F, 0.0F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "pro_mask_glass_iii",
                    box(48, 0, -2.62F, -6.2F, -5.43F, 5.24F, 3.15F, 0.16F, 0.0F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "right_hose_coupler_iii",
                    box(32, 18, -5.20F, -5.75F, -1.45F, 0.78F, 2.95F, 2.90F, 0.05F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "left_hose_coupler_iii",
                    box(40, 18, 4.42F, -5.75F, -1.45F, 0.78F, 2.95F, 2.90F, 0.05F),
                    PartPose.ZERO);
            head.addOrReplaceChild(
                    "right_hose_stub_iii",
                    box(32, 24, -5.72F, -4.85F, -0.62F, 1.0F, 1.0F, 1.0F, 0.10F),
                    PartPose.rotation(0.0F, 0.0F, -0.18F));
            head.addOrReplaceChild(
                    "left_hose_stub_iii",
                    box(36, 24, 4.72F, -4.85F, -0.62F, 1.0F, 1.0F, 1.0F, 0.10F),
                    PartPose.rotation(0.0F, 0.0F, 0.18F));
            head.addOrReplaceChild(
                    "single_lamp_iii",
                    box(24, 32, -1.35F, -9.38F, -3.45F, 2.7F, 1.55F, 2.15F, 0.03F),
                    PartPose.rotation(-0.16F, 0.0F, 0.0F));
            return;
        }

        // Tier IV: elite deep-sea pressure helmet. Strongly different silhouette.
        head.addOrReplaceChild(
                "deep_sea_dome_iv",
                box(0, 0, -4.15F, -8.65F, -4.15F, 8.3F, 8.35F, 8.3F, 1.28F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "deep_sea_rear_case_iv",
                box(0, 18, -3.75F, -7.2F, 3.95F, 7.5F, 6.2F, 2.0F, 0.10F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "deep_sea_face_frame_iv",
                box(20, 18, -3.65F, -7.05F, -5.72F, 7.3F, 5.35F, 0.82F, 0.05F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "deep_sea_glass_iv",
                box(48, 0, -3.02F, -6.47F, -5.98F, 6.04F, 4.16F, 0.18F, 0.0F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "helmet_chin_block_iv",
                box(36, 32, -2.25F, -2.35F, -5.28F, 4.5F, 2.2F, 1.2F, 0.04F),
                PartPose.ZERO);

        head.addOrReplaceChild(
                "right_lamp_iv",
                box(0, 40, -4.92F, -8.95F, -3.15F, 1.75F, 1.75F, 2.7F, 0.05F),
                PartPose.rotation(-0.10F, 0.0F, -0.12F));
        head.addOrReplaceChild(
                "left_lamp_iv",
                box(8, 40, 3.17F, -8.95F, -3.15F, 1.75F, 1.75F, 2.7F, 0.05F),
                PartPose.rotation(-0.10F, 0.0F, 0.12F));

        head.addOrReplaceChild(
                "right_pressure_coupler_iv",
                box(16, 40, -5.65F, -5.95F, -1.85F, 1.1F, 3.65F, 3.7F, 0.05F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "left_pressure_coupler_iv",
                box(24, 40, 4.55F, -5.95F, -1.85F, 1.1F, 3.65F, 3.7F, 0.05F),
                PartPose.ZERO);

        head.addOrReplaceChild(
                "top_cage_front_iv",
                box(32, 40, -3.2F, -10.35F, -3.0F, 6.4F, 0.55F, 0.65F, 0.05F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "top_cage_back_iv",
                box(32, 44, -3.2F, -10.35F, 2.35F, 6.4F, 0.55F, 0.65F, 0.05F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "top_cage_right_iv",
                box(48, 40, -3.2F, -10.35F, -2.35F, 0.65F, 0.55F, 4.7F, 0.05F),
                PartPose.ZERO);
        head.addOrReplaceChild(
                "top_cage_left_iv",
                box(54, 40, 2.55F, -10.35F, -2.35F, 0.65F, 0.55F, 4.7F, 0.05F),
                PartPose.ZERO);
    }

    private static void addChest(
            PartDefinition body,
            PartDefinition rightArm,
            PartDefinition leftArm,
            int tier) {
        if (tier == 1) {
            body.addOrReplaceChild(
                    "worn_wetsuit_i",
                    box(0, 0, -4.0F, 0.0F, -2.0F, 8.0F, 11.7F, 4.0F, 0.12F),
                    PartPose.ZERO);
            rightArm.addOrReplaceChild(
                    "right_thin_sleeve_i",
                    box(24, 0, -3.0F, -2.0F, -2.0F, 4.0F, 11.6F, 4.0F, 0.10F),
                    PartPose.ZERO);
            leftArm.addOrReplaceChild(
                    "left_thin_sleeve_i",
                    box(40, 0, -1.0F, -2.0F, -2.0F, 4.0F, 11.6F, 4.0F, 0.10F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "rope_harness_left_i",
                    box(0, 20, -3.0F, 0.5F, -2.28F, 0.55F, 9.4F, 0.24F, 0.0F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "rope_harness_right_i",
                    box(4, 20, 2.45F, 0.5F, -2.28F, 0.55F, 9.4F, 0.24F, 0.0F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "tiny_tank_i",
                    box(8, 20, -1.15F, 2.2F, 2.18F, 2.3F, 6.2F, 1.45F, 0.08F),
                    PartPose.ZERO);
            return;
        }

        if (tier == 2) {
            body.addOrReplaceChild(
                    "scuba_suit_ii",
                    box(0, 0, -4.0F, 0.0F, -2.0F, 8.0F, 12.0F, 4.0F, 0.32F),
                    PartPose.ZERO);
            rightArm.addOrReplaceChild(
                    "right_scuba_sleeve_ii",
                    box(24, 0, -3.0F, -2.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.28F),
                    PartPose.ZERO);
            leftArm.addOrReplaceChild(
                    "left_scuba_sleeve_ii",
                    box(40, 0, -1.0F, -2.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.28F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "harness_cross_ii",
                    box(0, 22, -3.25F, 1.15F, -2.48F, 6.5F, 6.6F, 0.28F, 0.0F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "single_tank_ii",
                    box(20, 22, -1.65F, 1.25F, 2.42F, 3.3F, 8.5F, 2.1F, 0.10F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "weight_belt_ii",
                    box(34, 22, -4.25F, 8.4F, -2.42F, 8.5F, 1.4F, 4.84F, 0.02F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "regulator_box_ii",
                    box(48, 22, -1.35F, 2.2F, -2.92F, 2.7F, 2.3F, 0.65F, 0.02F),
                    PartPose.ZERO);
            return;
        }

        if (tier == 3) {
            // Professional suit closely follows donor proportions: 0.74 body inflation and back rig.
            body.addOrReplaceChild(
                    "pro_scuba_body_iii",
                    box(0, 0, -4.0F, 0.0F, -2.0F, 8.0F, 12.0F, 4.0F, 0.74F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "pro_back_plate_iii",
                    box(16, 16, -2.0F, 0.0F, 3.25F, 4.0F, 12.2F, 1.0F, 0.72F),
                    PartPose.ZERO);

            rightArm.addOrReplaceChild(
                    "right_pro_arm_iii",
                    box(40, 16, -3.0F, -2.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.70F),
                    PartPose.ZERO);
            leftArm.addOrReplaceChild(
                    "left_pro_arm_iii",
                    mirroredBox(40, 16, -1.0F, -2.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.70F),
                    PartPose.ZERO);

            body.addOrReplaceChild(
                    "tank_left_iii",
                    box(0, 34, -3.25F, 1.1F, 3.0F, 2.2F, 8.9F, 2.1F, 0.12F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "tank_right_iii",
                    box(10, 34, 1.05F, 1.1F, 3.0F, 2.2F, 8.9F, 2.1F, 0.12F),
                    PartPose.ZERO);
            body.addOrReplaceChild(
                    "tank_manifold_iii",
                    box(20, 34, -1.35F, 0.65F, 3.35F, 2.7F, 1.55F, 1.4F, 0.04F),
                    PartPose.ZERO);

            rightArm.addOrReplaceChild(
                    "right_glove_cuff_iii",
                    box(32, 34, -3.28F, 6.55F, -2.45F, 4.55F, 3.1F, 4.9F, 0.12F),
                    PartPose.ZERO);
            leftArm.addOrReplaceChild(
                    "left_glove_cuff_iii",
                    box(48, 34, -1.27F, 6.55F, -2.45F, 4.55F, 3.1F, 4.9F, 0.12F),
                    PartPose.ZERO);
            return;
        }

        // Tier IV: armored deep-sea torso with very strong back silhouette.
        body.addOrReplaceChild(
                "pressure_body_iv",
                box(0, 0, -4.0F, -0.15F, -2.0F, 8.0F, 12.15F, 4.0F, 0.96F),
                PartPose.ZERO);
        body.addOrReplaceChild(
                "pressure_chest_plate_iv",
                box(16, 16, -3.65F, 1.0F, -3.18F, 7.3F, 7.6F, 0.82F, 0.06F),
                PartPose.ZERO);
        body.addOrReplaceChild(
                "pressure_collar_iv",
                box(36, 16, -4.25F, -0.85F, -2.75F, 8.5F, 1.55F, 5.5F, 0.12F),
                PartPose.ZERO);

        rightArm.addOrReplaceChild(
                "right_pressure_arm_iv",
                box(0, 30, -3.0F, -2.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.82F),
                PartPose.ZERO);
        leftArm.addOrReplaceChild(
                "left_pressure_arm_iv",
                mirroredBox(16, 30, -1.0F, -2.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.82F),
                PartPose.ZERO);

        rightArm.addOrReplaceChild(
                "right_pauldron_iv",
                box(32, 30, -3.95F, -2.78F, -2.8F, 5.2F, 2.3F, 5.6F, 0.10F),
                PartPose.ZERO);
        leftArm.addOrReplaceChild(
                "left_pauldron_iv",
                box(48, 30, -1.25F, -2.78F, -2.8F, 5.2F, 2.3F, 5.6F, 0.10F),
                PartPose.ZERO);

        body.addOrReplaceChild(
                "back_frame_iv",
                box(0, 44, -4.25F, 0.2F, 2.85F, 8.5F, 10.8F, 0.65F, 0.05F),
                PartPose.ZERO);
        body.addOrReplaceChild(
                "big_tank_left_iv",
                box(18, 44, -3.85F, 0.8F, 3.25F, 2.65F, 10.0F, 2.65F, 0.18F),
                PartPose.ZERO);
        body.addOrReplaceChild(
                "big_tank_right_iv",
                box(30, 44, 1.20F, 0.8F, 3.25F, 2.65F, 10.0F, 2.65F, 0.18F),
                PartPose.ZERO);
        body.addOrReplaceChild(
                "life_support_core_iv",
                box(42, 44, -1.2F, 2.3F, 3.65F, 2.4F, 5.8F, 2.15F, 0.08F),
                PartPose.ZERO);
        body.addOrReplaceChild(
                "lower_ballast_belt_iv",
                box(0, 56, -4.75F, 8.55F, -2.8F, 9.5F, 2.0F, 5.6F, 0.08F),
                PartPose.ZERO);

        rightArm.addOrReplaceChild(
                "right_gauntlet_iv",
                box(24, 56, -3.4F, 5.3F, -2.75F, 4.8F, 4.4F, 5.5F, 0.12F),
                PartPose.ZERO);
        leftArm.addOrReplaceChild(
                "left_gauntlet_iv",
                box(44, 56, -1.4F, 5.3F, -2.75F, 4.8F, 4.4F, 5.5F, 0.12F),
                PartPose.ZERO);
    }

    private static void addLegs(
            PartDefinition body,
            PartDefinition rightLeg,
            PartDefinition leftLeg,
            int tier) {
        if (tier == 1) {
            body.addOrReplaceChild(
                    "cheap_waist_i",
                    box(0, 0, -4.0F, 8.0F, -2.0F, 8.0F, 4.0F, 4.0F, 0.08F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_wetsuit_leg_i",
                    box(24, 0, -2.0F, 0.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.08F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_wetsuit_leg_i",
                    box(40, 0, -2.0F, 0.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.08F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_patch_i",
                    box(0, 18, -1.65F, 4.5F, -2.18F, 3.3F, 2.4F, 0.2F, 0.0F),
                    PartPose.ZERO);
            return;
        }

        if (tier == 2) {
            body.addOrReplaceChild(
                    "scuba_waist_ii",
                    box(0, 0, -4.0F, 8.0F, -2.0F, 8.0F, 4.0F, 4.0F, 0.28F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_scuba_leg_ii",
                    box(24, 0, -2.0F, 0.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.28F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_scuba_leg_ii",
                    box(40, 0, -2.0F, 0.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.28F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_knee_ii",
                    box(0, 18, -2.15F, 4.4F, -2.46F, 4.3F, 2.45F, 0.48F, 0.02F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_knee_ii",
                    box(14, 18, -2.15F, 4.4F, -2.46F, 4.3F, 2.45F, 0.48F, 0.02F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_thigh_strap_ii",
                    box(28, 18, -2.35F, 1.2F, -2.35F, 4.7F, 0.6F, 4.7F, 0.02F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_thigh_strap_ii",
                    box(44, 18, -2.35F, 1.2F, -2.35F, 4.7F, 0.6F, 4.7F, 0.02F),
                    PartPose.ZERO);
            return;
        }

        if (tier == 3) {
            // Donor-inspired 0.5 inflated SCUBA trousers.
            body.addOrReplaceChild(
                    "pro_waist_iii",
                    box(0, 0, -4.0F, 8.0F, -2.0F, 8.0F, 4.0F, 4.0F, 0.50F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_pro_leg_iii",
                    box(24, 0, -2.0F, 0.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.50F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_pro_leg_iii",
                    mirroredBox(40, 0, -2.0F, 0.0F, -2.0F, 4.0F, 12.0F, 4.0F, 0.50F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_ballast_iii",
                    box(0, 18, -3.02F, 1.7F, -1.0F, 1.0F, 4.4F, 2.0F, 0.05F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_ballast_iii",
                    box(8, 18, 2.02F, 1.7F, -1.0F, 1.0F, 4.4F, 2.0F, 0.05F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_shin_guard_iii",
                    box(16, 18, -2.3F, 6.0F, -2.62F, 4.6F, 4.1F, 0.72F, 0.04F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_shin_guard_iii",
                    box(32, 18, -2.3F, 6.0F, -2.62F, 4.6F, 4.1F, 0.72F, 0.04F),
                    PartPose.ZERO);
            return;
        }

        body.addOrReplaceChild(
                "pressure_waist_iv",
                box(0, 0, -4.0F, 7.8F, -2.0F, 8.0F, 4.2F, 4.0F, 0.78F),
                PartPose.ZERO);
        rightLeg.addOrReplaceChild(
                "right_pressure_leg_iv",
                box(24, 0, -2.0F, -0.1F, -2.0F, 4.0F, 12.1F, 4.0F, 0.72F),
                PartPose.ZERO);
        leftLeg.addOrReplaceChild(
                "left_pressure_leg_iv",
                box(40, 0, -2.0F, -0.1F, -2.0F, 4.0F, 12.1F, 4.0F, 0.72F),
                PartPose.ZERO);

        rightLeg.addOrReplaceChild(
                "right_hip_ballast_iv",
                box(0, 18, -3.35F, 0.8F, -1.45F, 1.15F, 5.0F, 2.9F, 0.10F),
                PartPose.ZERO);
        leftLeg.addOrReplaceChild(
                "left_hip_ballast_iv",
                box(8, 18, 2.20F, 0.8F, -1.45F, 1.15F, 5.0F, 2.9F, 0.10F),
                PartPose.ZERO);

        rightLeg.addOrReplaceChild(
                "right_knee_housing_iv",
                box(16, 18, -2.55F, 4.85F, -3.0F, 5.1F, 3.3F, 1.1F, 0.08F),
                PartPose.ZERO);
        leftLeg.addOrReplaceChild(
                "left_knee_housing_iv",
                box(34, 18, -2.55F, 4.85F, -3.0F, 5.1F, 3.3F, 1.1F, 0.08F),
                PartPose.ZERO);

        rightLeg.addOrReplaceChild(
                "right_shin_frame_iv",
                box(0, 30, -2.75F, 7.2F, -2.68F, 5.5F, 4.6F, 5.36F, 0.06F),
                PartPose.ZERO);
        leftLeg.addOrReplaceChild(
                "left_shin_frame_iv",
                box(22, 30, -2.75F, 7.2F, -2.68F, 5.5F, 4.6F, 5.36F, 0.06F),
                PartPose.ZERO);
    }

    private static void addBoots(
            PartDefinition rightLeg,
            PartDefinition leftLeg,
            int tier) {
        if (tier == 1) {
            rightLeg.addOrReplaceChild(
                    "right_rubber_boot_i",
                    box(0, 0, -2.15F, 7.5F, -2.25F, 4.3F, 4.5F, 4.5F, 0.16F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_rubber_boot_i",
                    box(20, 0, -2.15F, 7.5F, -2.25F, 4.3F, 4.5F, 4.5F, 0.16F),
                    PartPose.ZERO);
            return;
        }

        if (tier == 2) {
            rightLeg.addOrReplaceChild(
                    "right_scuba_boot_ii",
                    box(0, 0, -2.25F, 7.25F, -2.4F, 4.5F, 4.75F, 4.8F, 0.30F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_scuba_boot_ii",
                    box(20, 0, -2.25F, 7.25F, -2.4F, 4.5F, 4.75F, 4.8F, 0.30F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_small_fin_ii",
                    box(40, 0, -2.15F, 10.65F, -4.25F, 4.3F, 1.0F, 3.0F, 0.04F),
                    PartPose.rotation(0.06F, 0.0F, 0.0F));
            leftLeg.addOrReplaceChild(
                    "left_small_fin_ii",
                    box(40, 8, -2.15F, 10.65F, -4.25F, 4.3F, 1.0F, 3.0F, 0.04F),
                    PartPose.rotation(0.06F, 0.0F, 0.0F));
            return;
        }

        if (tier == 3) {
            // Donor shoe proportions with the very distinctive long front fin.
            rightLeg.addOrReplaceChild(
                    "right_pro_boot_iii",
                    box(0, 0, -2.0F, 7.0F, -2.0F, 4.0F, 5.0F, 4.0F, 0.75F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_pro_boot_iii",
                    box(20, 0, -2.0F, 7.0F, -2.0F, 4.0F, 5.0F, 4.0F, 0.75F),
                    PartPose.ZERO);
            rightLeg.addOrReplaceChild(
                    "right_long_fin_iii",
                    box(40, 0, -2.15F, 10.55F, -6.0F, 4.3F, 1.25F, 5.0F, 0.06F),
                    PartPose.rotation(0.08F, 0.0F, 0.0F));
            leftLeg.addOrReplaceChild(
                    "left_long_fin_iii",
                    box(40, 8, -2.15F, 10.55F, -6.0F, 4.3F, 1.25F, 5.0F, 0.06F),
                    PartPose.rotation(0.08F, 0.0F, 0.0F));
            rightLeg.addOrReplaceChild(
                    "right_heel_weight_iii",
                    box(0, 16, -2.55F, 9.25F, 1.85F, 5.1F, 2.0F, 1.2F, 0.04F),
                    PartPose.ZERO);
            leftLeg.addOrReplaceChild(
                    "left_heel_weight_iii",
                    box(16, 16, -2.55F, 9.25F, 1.85F, 5.1F, 2.0F, 1.2F, 0.04F),
                    PartPose.ZERO);
            return;
        }

        // Elite deep-sea boots: no "normal boot" silhouette left.
        rightLeg.addOrReplaceChild(
                "right_deep_boot_iv",
                box(0, 0, -2.8F, 6.8F, -3.0F, 5.6F, 5.2F, 6.0F, 0.22F),
                PartPose.ZERO);
        leftLeg.addOrReplaceChild(
                "left_deep_boot_iv",
                box(24, 0, -2.8F, 6.8F, -3.0F, 5.6F, 5.2F, 6.0F, 0.22F),
                PartPose.ZERO);
        rightLeg.addOrReplaceChild(
                "right_ballast_sole_iv",
                box(0, 20, -3.25F, 11.05F, -3.45F, 6.5F, 1.35F, 6.9F, 0.06F),
                PartPose.ZERO);
        leftLeg.addOrReplaceChild(
                "left_ballast_sole_iv",
                box(26, 20, -3.25F, 11.05F, -3.45F, 6.5F, 1.35F, 6.9F, 0.06F),
                PartPose.ZERO);
        rightLeg.addOrReplaceChild(
                "right_stabilizer_fin_iv",
                box(0, 30, -2.65F, 10.1F, -6.4F, 5.3F, 1.2F, 3.6F, 0.05F),
                PartPose.rotation(0.05F, 0.0F, 0.0F));
        leftLeg.addOrReplaceChild(
                "left_stabilizer_fin_iv",
                box(22, 30, -2.65F, 10.1F, -6.4F, 5.3F, 1.2F, 3.6F, 0.05F),
                PartPose.rotation(0.05F, 0.0F, 0.0F));

        rightLeg.addOrReplaceChild(
                "right_ankle_module_iv",
                box(44, 30, 2.45F, 7.8F, -1.8F, 0.95F, 3.6F, 3.6F, 0.08F),
                PartPose.ZERO);
        leftLeg.addOrReplaceChild(
                "left_ankle_module_iv",
                box(52, 30, -3.4F, 7.8F, -1.8F, 0.95F, 3.6F, 3.6F, 0.08F),
                PartPose.ZERO);
    }
}
