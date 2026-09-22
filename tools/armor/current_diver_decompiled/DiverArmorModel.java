/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  com.mojang.blaze3d.vertex.PoseStack
 *  com.mojang.blaze3d.vertex.VertexConsumer
 *  net.minecraft.client.Minecraft
 *  net.minecraft.client.model.HumanoidModel
 *  net.minecraft.client.model.geom.ModelPart
 *  net.minecraft.client.model.geom.builders.LayerDefinition
 *  net.minecraft.client.renderer.RenderType
 *  net.minecraft.resources.ResourceLocation
 *  net.minecraft.world.entity.EquipmentSlot
 *  net.minecraft.world.entity.LivingEntity
 */
package ru.koshpack.forgebridge.armor.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import ru.koshpack.forgebridge.armor.client.DiverModelGeometry;

public final class DiverArmorModel
extends HumanoidModel<LivingEntity> {
    private final ResourceLocation texture;

    public DiverArmorModel(ModelPart modelPart, ResourceLocation resourceLocation) {
        super(modelPart);
        this.texture = resourceLocation;
    }

    public static LayerDefinition createLayer(EquipmentSlot equipmentSlot, int n) {
        return DiverModelGeometry.create(equipmentSlot, n);
    }

    public void renderToBuffer(PoseStack poseStack, VertexConsumer vertexConsumer, int n, int n2, int n3) {
        VertexConsumer vertexConsumer2 = Minecraft.getInstance().renderBuffers().bufferSource().getBuffer(RenderType.entityTranslucent((ResourceLocation)this.texture));
        super.renderToBuffer(poseStack, vertexConsumer2, n, n2, n3);
    }
}

