// KoshPack professional armor crafting runtime v1.
// 17 professions x 4 armor pieces x 4 tiers.
//
// Progression:
// I   — workbench / improvised workwear.
// II  — previous armor + profession module + Foundry-cast steel reinforcement.
// III — previous armor + industrial module + Foundry-cast Crimson Steel reinforcement.
// IV  — previous armor + master module + Foundry-cast Tyrian Steel reinforcement.
//
// Smithing is deliberately used for II -> IV so the base stack's components/state are preserved.

const ARMOR_PIECES = [
  { id: 'helmet', tier1Extra: ['minecraft:leather', 'minecraft:string'] },
  { id: 'chestplate', tier1Extra: ['2x minecraft:leather', '2x minecraft:white_wool'] },
  { id: 'leggings', tier1Extra: ['2x minecraft:leather', 'minecraft:white_wool'] },
  { id: 'boots', tier1Extra: ['2x minecraft:leather'] }
]

const ARMOR_CASTS = {
  helmet: 'sgearmetalworks:helmet_cast',
  chestplate: 'sgearmetalworks:chestplate_cast',
  leggings: 'sgearmetalworks:leggings_cast',
  boots: 'sgearmetalworks:boots_cast'
}

const CAST_AMOUNTS = {
  helmet: 270,
  chestplate: 360,
  leggings: 360,
  boots: 180
}

const ARMOR_TIERS = [
  { id: 'ii', prev: 'i', fluid: 'c:molten_steel' },
  { id: 'iii', prev: 'ii', fluid: 'c:molten_crimson_steel' },
  { id: 'iv', prev: 'iii', fluid: 'c:molten_tyrian_steel' }
]

const PROFESSIONS = [
  {
    id: 'miner', namespace: 'koshpackminerhelmet', itemPrefix: 'miner',
    moduleI: ['3x minecraft:flint', '2x minecraft:copper_ingot', '2x minecraft:coal'],
    moduleII: ['minecraft:lantern', '2x minecraft:iron_ingot'],
    moduleIII: ['create:precision_mechanism', 'minecraft:quartz', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:diamond']
  },
  {
    id: 'engineer', namespace: 'koshpackengineerhelmet', itemPrefix: 'engineer',
    moduleI: ['3x minecraft:copper_ingot', '3x minecraft:redstone', '2x minecraft:iron_ingot'],
    moduleII: ['create:precision_mechanism', '2x minecraft:copper_ingot'],
    moduleIII: ['create:precision_mechanism', 'minecraft:redstone_block', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'create:precision_mechanism']
  },
  {
    id: 'scout', namespace: 'koshpackscouthelmet', itemPrefix: 'scout',
    moduleI: ['minecraft:spyglass', '2x minecraft:leather', '2x minecraft:feather', 'minecraft:string'],
    moduleII: ['minecraft:spyglass', 'minecraft:compass'],
    moduleIII: ['create:brass_sheet', 'minecraft:ender_pearl', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:echo_shard']
  },
  {
    id: 'builder', namespace: 'koshpackbuilderhelmet', itemPrefix: 'builder',
    moduleI: ['3x minecraft:brick', '2x minecraft:string', '2x minecraft:iron_ingot'],
    moduleII: ['minecraft:scaffolding', '2x minecraft:iron_ingot'],
    moduleIII: ['create:precision_mechanism', 'minecraft:quartz', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:diamond']
  },
  {
    id: 'medic', namespace: 'koshpackmedichelmet', itemPrefix: 'medic',
    moduleI: ['3x minecraft:white_wool', '2x minecraft:paper', 'minecraft:honey_bottle', 'minecraft:gold_ingot'],
    moduleII: ['minecraft:honey_bottle', 'minecraft:golden_carrot'],
    moduleIII: ['minecraft:ghast_tear', 'minecraft:blaze_powder', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:ghast_tear']
  },
  {
    id: 'farmer', namespace: 'koshpackfarmerhelmet', itemPrefix: 'farmer',
    moduleI: ['3x minecraft:wheat', '2x minecraft:leather', '2x minecraft:string'],
    moduleII: ['minecraft:shears', 'minecraft:iron_hoe'],
    moduleIII: ['create:brass_sheet', 'minecraft:golden_carrot', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:golden_carrot']
  },
  {
    id: 'blacksmith', namespace: 'koshpackblacksmithhelmet', itemPrefix: 'blacksmith',
    moduleI: ['3x minecraft:brick', '2x minecraft:coal', '2x minecraft:leather'],
    moduleII: ['minecraft:blast_furnace', 'minecraft:iron_ingot'],
    moduleIII: ['minecraft:blaze_rod', 'minecraft:magma_cream', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:netherite_scrap']
  },
  {
    id: 'fisher', namespace: 'koshpackfisherhelmet', itemPrefix: 'fisher',
    moduleI: ['3x minecraft:string', '2x minecraft:cod', '2x minecraft:leather'],
    moduleII: ['minecraft:fishing_rod', 'minecraft:prismarine_shard'],
    moduleIII: ['create:brass_sheet', 'minecraft:prismarine_crystals', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:heart_of_the_sea']
  },
  {
    id: 'lumberjack', namespace: 'koshpacklumberjackhelmet', itemPrefix: 'lumberjack',
    moduleI: ['3x minecraft:oak_log', '2x minecraft:iron_ingot', '2x minecraft:leather'],
    moduleII: ['minecraft:iron_axe', 'minecraft:chain'],
    moduleIII: ['create:brass_sheet', 'minecraft:diamond', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:diamond_axe']
  },
  {
    id: 'diver', namespace: 'koshpackdiverhelmet', itemPrefix: 'diver',
    moduleI: ['3x minecraft:copper_ingot', '2x minecraft:glass', '2x minecraft:dried_kelp'],
    moduleII: ['minecraft:nautilus_shell', 'minecraft:glass', 'minecraft:copper_ingot'],
    moduleIII: ['create:copper_backtank', 'minecraft:heart_of_the_sea', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:heart_of_the_sea']
  },
  {
    id: 'fighter', namespace: 'koshpackfighterarmor', itemPrefix: 'fighter',
    moduleI: ['3x minecraft:iron_ingot', '2x minecraft:leather', '2x minecraft:flint'],
    moduleII: ['minecraft:shield', 'minecraft:iron_ingot'],
    moduleIII: ['minecraft:blaze_rod', 'minecraft:diamond', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:netherite_scrap']
  },
  {
    id: 'archer', namespace: 'koshpackarcherarmor', itemPrefix: 'archer',
    moduleI: ['3x minecraft:feather', '3x minecraft:string', '2x minecraft:leather'],
    moduleII: ['minecraft:bow', 'minecraft:leather'],
    moduleIII: ['create:brass_sheet', 'minecraft:phantom_membrane', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:ender_eye']
  },
  {
    id: 'shooter', namespace: 'koshpackshooterarmor', itemPrefix: 'shooter',
    moduleI: ['3x minecraft:gunpowder', '2x minecraft:copper_ingot', '2x minecraft:iron_ingot'],
    moduleII: ['minecraft:crossbow', 'minecraft:iron_ingot'],
    moduleIII: ['create:brass_sheet', 'minecraft:spyglass', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:spyglass']
  },
  {
    id: 'artillery', namespace: 'koshpackartilleryarmor', itemPrefix: 'artillery',
    moduleI: ['3x minecraft:gunpowder', '3x minecraft:brick', '2x minecraft:iron_ingot'],
    moduleII: ['minecraft:tnt', 'minecraft:iron_ingot'],
    moduleIII: ['minecraft:blaze_rod', '2x minecraft:tnt', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:netherite_scrap']
  },
  {
    id: 'hunter', namespace: 'koshpackhunterarmor', itemPrefix: 'hunter',
    moduleI: ['3x minecraft:leather', '2x minecraft:bone', '2x minecraft:string'],
    moduleII: ['minecraft:spyglass', 'minecraft:lead'],
    moduleIII: ['create:brass_sheet', 'minecraft:rabbit_hide', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:echo_shard']
  },
  {
    id: 'researcher', namespace: 'koshpackresearcherarmor', itemPrefix: 'researcher',
    moduleI: ['minecraft:compass', '3x minecraft:paper', '2x minecraft:leather'],
    moduleII: ['minecraft:spyglass', 'minecraft:compass'],
    moduleIII: ['create:brass_sheet', 'minecraft:amethyst_shard', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:echo_shard']
  },
  {
    id: 'pilot', namespace: 'koshpackpilothelmet', itemPrefix: 'pilot',
    moduleI: ['2x minecraft:glass', '3x minecraft:string', '2x minecraft:copper_ingot'],
    moduleII: ['create:precision_mechanism', 'minecraft:phantom_membrane'],
    moduleIII: ['create:precision_mechanism', 'minecraft:phantom_membrane', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:phantom_membrane']
  }
]

function armorId(prof, piece, tier) {
  return `${prof.namespace}:${prof.itemPrefix}_${piece}_${tier}_test`
}

function moduleId(prof, tier) {
  return `kubejs:${prof.id}_module_${tier}`
}

ServerEvents.recipes(event => {
  // Foundry casting: reusable Silent Gear Metalworks armor casts -> KoshPack reinforcement parts.
  ARMOR_TIERS.forEach(tier => {
    ARMOR_PIECES.forEach(piece => {
      const out = `kubejs:armor_reinforcement_${piece.id}_${tier.id}`
      event.custom({
        type: 'productivemetalworks:item_casting',
        cast: { item: ARMOR_CASTS[piece.id] },
        consume_cast: false,
        fluid: {
          amount: CAST_AMOUNTS[piece.id],
          tag: tier.fluid
        },
        result: {
          count: 1,
          id: out
        }
      }).id(`kubejs:armor/foundry/${piece.id}_${tier.id}`)
    })
  })

  PROFESSIONS.forEach(prof => {
    // Remove any direct/legacy recipes for the visual armor items before installing the progression chain.
    ;['i', 'ii', 'iii', 'iv'].forEach(tier => {
      ARMOR_PIECES.forEach(piece => event.remove({ output: armorId(prof, piece.id, tier) }))
    })

    // Profession module chain.
    event.shapeless(moduleId(prof, 'i'), prof.moduleI)
      .id(`kubejs:armor/modules/${prof.id}_i`)

    event.shapeless(moduleId(prof, 'ii'), [moduleId(prof, 'i'), ...prof.moduleII])
      .id(`kubejs:armor/modules/${prof.id}_ii`)

    event.shapeless(moduleId(prof, 'iii'), [moduleId(prof, 'ii'), ...prof.moduleIII])
      .id(`kubejs:armor/modules/${prof.id}_iii`)

    event.shapeless(moduleId(prof, 'iv'), [moduleId(prof, 'iii'), ...prof.moduleIV])
      .id(`kubejs:armor/modules/${prof.id}_iv`)

    // Tier I: deliberately cheap workbench assembly; no Foundry required yet.
    ARMOR_PIECES.forEach(piece => {
      event.shapeless(
        armorId(prof, piece.id, 'i'),
        [moduleId(prof, 'i'), ...piece.tier1Extra]
      ).id(`kubejs:armor/assembly/${prof.id}/${piece.id}_i`)
    })

    // Tiers II-IV: strict sequential smithing. Previous armor is always the base item.
    ARMOR_TIERS.forEach(tier => {
      ARMOR_PIECES.forEach(piece => {
        event.smithing(
          armorId(prof, piece.id, tier.id),
          moduleId(prof, tier.id),
          armorId(prof, piece.id, tier.prev),
          `kubejs:armor_reinforcement_${piece.id}_${tier.id}`
        ).id(`kubejs:armor/upgrade/${prof.id}/${piece.id}_${tier.id}`)
      })
    })
  })
})
