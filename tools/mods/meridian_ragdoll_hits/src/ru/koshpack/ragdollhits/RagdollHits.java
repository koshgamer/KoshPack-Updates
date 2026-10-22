package ru.koshpack.ragdollhits;

import com.mojang.logging.LogUtils;
import dev.leo.sableplayerragdoll.block.RagdollPartBlock;
import dev.leo.sableplayerragdoll.mob.MobRagdollAssembly;
import dev.leo.sableplayerragdoll.mob.block.MobRagdollPartBlock;
import dev.leo.sableplayerragdoll.physics.RagdollSessionManager;
import dev.ryanhcode.sable.api.sublevel.SubLevelContainer;
import dev.ryanhcode.sable.sublevel.ServerSubLevel;
import dev.ryanhcode.sable.sublevel.SubLevel;
import dev.ryanhcode.sable.sublevel.plot.LevelPlot;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.player.AttackEntityEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import org.slf4j.Logger;

/**
 * Sable: Ragdolls hides a ragdolled player or mob from picking and direct attacks; the visible body is made of
 * physics blocks on a Sable sub-level. Mob parts forward a block attack to the mob only on the survival path, and
 * player parts never forward it. This turns a left click on any ragdoll part into a real melee attack on its owner.
 */
@Mod(RagdollHits.MOD_ID)
public final class RagdollHits {
    public static final String MOD_ID = "meridian_ragdoll_hits";
    private static final Logger LOG = LogUtils.getLogger();

    public RagdollHits() {
        NeoForge.EVENT_BUS.addListener(EventPriority.HIGHEST, RagdollHits::onLeftClickBlock);
        NeoForge.EVENT_BUS.addListener(EventPriority.HIGHEST, RagdollHits::onAttackEntity);
    }

    /**
     * Direct attacks on the hidden source entity (Better Combat swing targeting, vanilla attack packets) reach
     * Player#attack, which then drops them because Sable: Ragdolls makes the entity non-attackable outside its own
     * attack pipe. Re-run the attack inside that pipe.
     */
    private static void onAttackEntity(AttackEntityEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer attacker) || pipeActive()) return;
        Entity target = event.getTarget();
        if (!isRagdolled(target)) return;
        event.setCanceled(true);
        float before = target instanceof LivingEntity living ? living.getHealth() : 0;
        RagdollSessionManager.RAGDOLL_PIPE_ACTIVE.set(true);
        try {
            attacker.attack(target);
        } finally {
            RagdollSessionManager.RAGDOLL_PIPE_ACTIVE.set(false);
        }
        LOG.info("[ragdoll_hits] {} attacked ragdolled {}: health {} -> {}", attacker.getScoreboardName(),
                target.getName().getString(), before, target instanceof LivingEntity living ? living.getHealth() : 0);
    }

    private static boolean pipeActive() {
        return Boolean.TRUE.equals(RagdollSessionManager.RAGDOLL_PIPE_ACTIVE.get())
                || Boolean.TRUE.equals(MobRagdollAssembly.RAGDOLL_PIPE_ACTIVE.get());
    }

    private static boolean isRagdolled(Entity target) {
        if (target instanceof ServerPlayer player) return RagdollSessionManager.isPlayerCurrentlyRagdolled(player);
        return MobRagdollAssembly.isConverted(target.getUUID());
    }

    private static void onLeftClickBlock(PlayerInteractEvent.LeftClickBlock event) {
        if (!(event.getLevel() instanceof ServerLevel level) || !(event.getEntity() instanceof ServerPlayer attacker)) return;
        if (event.getAction() != PlayerInteractEvent.LeftClickBlock.Action.START) return;
        BlockPos pos = event.getPos();
        BlockState state = level.getBlockState(pos);

        if (state.getBlock() instanceof RagdollPartBlock) {
            ServerPlayer victim = ragdollOwner(level, pos);
            boolean hit = victim != null && victim != attacker && victim.isAlive();
            if (hit) {
                float before = victim.getHealth();
                RagdollSessionManager.RAGDOLL_PIPE_ACTIVE.set(true);
                try {
                    attacker.attack(victim);
                } finally {
                    RagdollSessionManager.RAGDOLL_PIPE_ACTIVE.set(false);
                }
                LOG.info("[ragdoll_hits] {} hit ragdolled player {}: health {} -> {}", attacker.getScoreboardName(),
                        victim.getScoreboardName(), before, victim.getHealth());
            } else {
                LOG.info("[ragdoll_hits] {} clicked a player ragdoll part at {}, owner {}", attacker.getScoreboardName(),
                        pos, victim == null ? "not found" : victim.getScoreboardName());
            }
            event.setCanceled(true);
        } else if (state.getBlock() instanceof MobRagdollPartBlock) {
            // Same handler the mod runs on the survival path (MobRagdollPartBlock#attack); creative skips it.
            state.attack(level, pos, attacker);
            LOG.info("[ragdoll_hits] {} hit a mob ragdoll part at {}", attacker.getScoreboardName(), pos);
            event.setCanceled(true);
        }
    }

    private static ServerPlayer ragdollOwner(ServerLevel level, BlockPos pos) {
        SubLevelContainer container = SubLevelContainer.getContainer(level);
        if (container == null || !container.inBounds(pos)) return null;
        LevelPlot plot = container.getPlot(new ChunkPos(pos));
        if (plot == null) return null;
        SubLevel subLevel = plot.getSubLevel();
        if (!(subLevel instanceof ServerSubLevel server)) return null;
        UUID playerId = RagdollSessionManager.getPlayerId(server);
        return playerId == null ? null : level.getServer().getPlayerList().getPlayer(playerId);
    }
}
