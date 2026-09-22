// KoshPack Forge Bench developer test kit.
// Command: /forge_test_kit
// Requires permission level 2. Intended for DEV validation only.

function koshForgeTestGive(player, id, count) {
  try {
    player.give(Item.of(id, count))
    return true
  } catch (e) {
    player.tell(Text.red('Не удалось выдать: ' + id))
    return false
  }
}

function koshForgeTestGiveTag(player, tag, count, fallback) {
  try {
    var stack = Ingredient.of(tag).getFirst()
    if (stack && !stack.empty) {
      var out = stack.copy()
      out.count = count
      player.give(out)
      return true
    }
  } catch (e) {}

  if (fallback) return koshForgeTestGive(player, fallback, count)
  player.tell(Text.red('В сборке нет предмета для тега ' + tag))
  return false
}

ServerEvents.commandRegistry(function(event) {
  var Commands = event.commands

  event.register(
    Commands.literal('forge_test_kit')
      .requires(function(source) { return source.hasPermission(2) })
      .executes(function(ctx) {
        var player = ctx.source.getPlayerOrException()

        var fixed = [
          ['kubejs:forge_bench', 1],

          ['koshpackminerhelmet:miner_helmet_iv_test', 1],
          ['koshpackminerhelmet:miner_chestplate_iv_test', 1],
          ['koshpackminerhelmet:miner_leggings_iv_test', 1],
          ['koshpackminerhelmet:miner_boots_iv_test', 1],

          ['minecraft:diamond_sword', 1],
          ['minecraft:diamond_pickaxe', 1],
          ['minecraft:diamond_shovel', 1],
          ['minecraft:diamond_hoe', 1],
          ['minecraft:bow', 1],
          ['minecraft:crossbow', 1],
          ['minecraft:trident', 1],
          ['minecraft:shears', 1],
          ['minecraft:fishing_rod', 1],

          ['kubejs:base_abrasive', 64],
          ['kubejs:industrial_abrasive', 64],
          ['kubejs:heat_resistant_binder', 64],
          ['kubejs:finishing_abrasive', 64],
          ['create:precision_mechanism', 64],

          ['minecraft:amethyst_shard', 64],
          ['minecraft:blaze_powder', 64],
          ['minecraft:brick', 64],
          ['minecraft:chain', 64],
          ['minecraft:clay_ball', 64],
          ['minecraft:coal', 64],
          ['minecraft:copper_ingot', 64],
          ['minecraft:diamond', 64],
          ['minecraft:dried_kelp', 64],
          ['minecraft:feather', 64],
          ['minecraft:fire_charge', 64],
          ['minecraft:flint', 64],
          ['minecraft:glass', 64],
          ['minecraft:glow_berries', 64],
          ['minecraft:gold_ingot', 64],
          ['minecraft:gold_nugget', 64],
          ['minecraft:honeycomb', 64],
          ['minecraft:iron_ingot', 64],
          ['minecraft:iron_nugget', 64],
          ['minecraft:leather', 64],
          ['minecraft:magma_cream', 64],
          ['minecraft:obsidian', 64],
          ['minecraft:packed_ice', 64],
          ['minecraft:prismarine_shard', 64],
          ['minecraft:quartz', 64],
          ['minecraft:rabbit_hide', 64],
          ['minecraft:redstone', 64],
          ['minecraft:sculk_sensor', 64],
          ['minecraft:slime_ball', 64],
          ['minecraft:soul_sand', 64],
          ['minecraft:soul_soil', 64],
          ['minecraft:stick', 64],
          ['minecraft:string', 64],
          ['minecraft:tinted_glass', 64],
          ['minecraft:white_wool', 64]
        ]

        for (var i = 0; i < fixed.length; i++) {
          koshForgeTestGive(player, fixed[i][0], fixed[i][1])
        }

        koshForgeTestGiveTag(player, '#c:ingots/steel', 64, null)
        koshForgeTestGiveTag(player, '#c:ingots/crimson_steel', 64, 'silentgear:crimson_steel_ingot')
        koshForgeTestGiveTag(player, '#c:ingots/tyrian_steel', 64, 'silentgear:tyrian_steel_ingot')

        player.tell(Text.green('Набор для теста кузнечного стенда выдан.'))
        return 1
      })
  )
})
