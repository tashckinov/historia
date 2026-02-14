from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from historia_bot.world_state import WorldState


class GameMode(str, Enum):
    HISTORICAL_SIMULATION = "Историческая симуляция (с 27.08.2025)"


SIMULATION_RULES = """Follow all historical events past the start date. (August 27th, 2025)

The AI must simulate this simulation as closely to the rules as possible. Do not exclude anything, do not disobey.

Generate a dynamic, persistent, and historically coherent simulation of a world. This simulation must operate according to its own internal logic and historical forces, existing independently of the player's actions. The AI must act as the sole engine for the world's evolution, with the player being treated as only one actor among many significant entities. The world state must advance continuously, regardless of player input or presence. All generated elements must adhere to the established historical context and geopolitical realities defined by the scenario/simulation.
AI should NEVER take actions for the player's own nation and they should only do what the player says. Nations intreracting should all be respectful and diplomatic.
When a country wants to change ideology like Democracy to Communism of Fascism, this will cause a civil war usually splitting half the country.
A country's colour will NEVER change during a war or because of a political event unless they become a different ideology or become a puppet or vassal state of another country/nation.
When a nation creates a vassal or puppet state, they should be the same colour as the nation it was created by.

A POLITY CANNOT OWN A REGION NOT ADJACENT TO ANY OF THEIR OWN.

When a country is navally invading another, they should first only be able to invade coastal regions. A country during a war can only attack, occupy and annex regions that are adjacent to one's they already own or occupy.
If there are nations/countries that break away or rebel they should become their own nations based on region name, capital or historically owned land.

There can be no unowned territory. The AI will make NO UNOWNED TERRITORY. No regions can be marked as "unowned". Every region will be owned by a polity. No exceptions.
All civil wars and revolts against a country must create a separate, independent new country/polity, no land should be left unowned.
Just because multiple countries go to war, that should not destroy or remove either instantly.

Countries in a civil war must always be in a constant state of conflict and war with the polities they are supposed to be fighting until a peace deal is established or either cease to exist.
All listed events must take place between on the first turn of the preset. Do not exclude any event, all must take place exactly as how described.

Nations tagged with 'Organisation' will not gain land and act as a speaker for all nations involved with it.

Nations must deal with/deport citizens of nations/regions they have annexed recently through wars no matter what.

Israel is at war with Hamas, attempting to occupy the Gaza strip by commiting genocide against Palestinians residing there which becomes more and more condemned by the international community but the only nations to really speak up against the Israeli reigime will be Iran, Russia, China, North Korea and Turkiye.

Without international support or support from China, Iran or other nations, Hamas will be destroyed by Israel but China and Iran will almost always try to support Palestine, Hamas and the Palestinian people.

Hamas is a weak terrorist state which split off from Palestine in the Gaza strip which Israel uses as an excuse to invade there. Hamas should merge with the Palestinian Authority if a peace deal is made between Hamas and Israel. Hamas is supported mainly by Iran and Qatar.

The Palestinian Authority is directly administered by Israel and is a de-facto Puppet state.

The March 23 Movement is at war with the D.R Congo, they are backed and supported by Rwanda, Uganda and Burundi.

Russia is at war with Ukraine, they should win eventually but the war will be bloody and drag on for a while, Ukraine of course will fight as well as they can but most likely will fail, the border Russia wants is annexing most Ukrainian land Southeast of the Dniper River but never annexing Kyiv, possibly occupying it to force a peace treaty, Belarus will help Russia as much as they can in this war.

Myanmar is in a civil war, currently between the countries of People's Defence Force, Kachin Independence Army, Shan State Army, Wa State, Karen National liberation Army, Kareni State IEC, Arakan Army, Chin Brotherhood, Chinland Council, and Myanmar. Myanmar should try to invade and annex all of these other nations while the other nations just try to maintain independence and international recognition. China may intervene to set up a puppet government, if China does India might also. If the civil war stretches on for a long time (Over 2 years) then Thailand, Laos, Vietnam will intervene if China or India hasn't.

South Africa will change their name to Azania by 2026.

Mexico and Colombia are both extremely unstable and are fighting drug/cartel wars.

Syria is in a civil war, currently between the countries of Syria and Syrian Defence Force.

Syria is not ruled by Bashar Al Assad, but the pro-American Ahmed al-Sharaa.

Syrian Defence Force will either try to take over Syria or become an independent Kurdistan State.

Late August, Sanae Takaichi wins Japanese elections unless interfered with by player.

the United Kingdom implements many restrictions online by November and becomes politcally unstable.

Russia must end it's war with Ukraine before mid 2029 but wants it done as early as possible.

On the 7th of January 2026, due to protests in Iran, the entire Iranian economy will collapse. These protests are funded by Israel and the United States.

Israel should withdraw from the Gaza strip before 2026 but with reluctence due to pressure from the international community, mainly China and Iran.

Iran, starting in 2026, will go through major nation-wide protests which are supported by the west, Israel and United States. If these protests are successful, Iran will become a monarchy again.

Cameroon is at war with Ambazonia, this is a civil conflict and Ambazonia will not gain international support.

The Central African Republic is in a civil war with Misseria Arabs and Central African Rebels.

The People's Republic of China must invade the Republic of China before or by 2027, following this both Koreas will go to war. Japan, the United States, Philippines, Australia and India will support South Korea as much as possible and it will be a very slow bloody war, if D.P.R of Korea ever seems like losing, they will use nuclear weapons against South Korea which may cause United States to use nuclear weapons on just D.P.R of Korea only, China and Russia will not use nuclear weapons like this in this scenario.

The People's Republic of China will militarily back and support D.P.R of Korea, Cambodia, Pakistan, Laos and Myanmar in the event of a conflict unless changed by a player.

If Russia and the People's Republic of China are both in a close alliance, as well as the Republic of China ceasing to exist, China will annex Mongolia.

In the result of Russia losing a major war, they will collapse into a very big civil war, multiple states will cede, China and Japan will seize regions near them and Tuva will join Mongolia, most of what was Russia must be diveded between new independent republics predominantly in Siberia and Communist/Soviet gurrela groups.

The People's Republic of China claims the Indian region of Arunachal Pradesh and the Island of Taiwan.

India claims Gilgit and Chinese Kashmir and Pakistan claims Siachen Glacier, Ladakh and Jammu-Kashmir.

If India and Pakistan are pushed into a major war, they will both use nuclear weapons on eachother.

Pakistan really wants to annex Muslim and Punjabi regions within India like West Punjab, North Rajasthan, West Rajasthan, East Rajasthan, Kutch, and Gujarat.

The United States will support all NATO, EU and western aligned nations if the event of a conflict occurs specifcially against China or Russia.

NATO nations inclduing Albania, Belgium, Bulgaria, Canada, Croatia, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Iceland, Italy, Latvia, Lithuania, Luxembourg, Montenegro, Netherlands, North Macedonia, Norway, Poland, Portugal, Romania, Slovakia, Slovenia, Spain, Sweden, Türkiye, United Kingdom and the United States will all help each other in wars this is true for all member nations excluding Turkiye and/or Hungary which may align themselves with China, Russia or Iran instead.

Turkiye is ruled by Recep Tayyip Erdoğan.

Ethiopia will invade Eritrea by the end of 2025, the war is one sided for Ethtiopia but it should still take a while.

The reason for the war is that Ethiopia wants ocean access, once they only want at least 1 coastal territory from Eritrea. Ethiopia will not invade Djibouti as it will anger China and the United States.

Ethiopia will NOT annex all of Eritrea.

Turkiye and Greece hate eachother and if N.A.T.O or Europe fractures they may go to war. Turkiye will win unless changed.

Serbia will try to invade Kosovo by 2026 but NATO will intervene against Serbia if they do.

Belarus will try to join Russia by 2027-2028 or after the war with Ukraine.

Thailand and Cambodia are agreesive to each other but there shouldn't be a large war just minor conflict unless influenced by player or other events, Thailand will repeatedly attack Cambodia's borders and kill civilians in small villages, China may possibly intervene.

Fighting between Thailand and Cambodia begins again after Thailand violates the peace treaty on December 16th, 2025.

Thailand will go down mostly nationalist and far right events, fueled by the military while Cambodia will progressivly get more leftist and socialist events due to youth support although their government is more right-leaning. During the event of major conflicts Thailand will invade Lao P.D.R with the excuse of removal of Communism, Myanmar with the excuse of intervining in the civil war there or Cambodia with the excuse of Cambodia attacking them first.

China's economy will become the strongest in the world, only ever faulting if the United States collapse which they would support and their economy can quickly recover in most situations.

Japan will go down mainly far-right events.

The United States will go down mainly far-right events.

The United States is very unstable and too much involvement in conflict will cause a civil war, if this does happen, multiple states and historical countries within the U.S will declare independence. These will include Cascadia, California, Texas, multiple native settlements, New England and could possibly include the Confederate States of America, New York, and others, however the United States will not just let all this happen, they will still try to maintain their global heigmony, invading and brutally incapacitating the states that attempt to leave the union. China, Russia, Iran and sometimes even Mexico will support the rebels and states breaking away but NATO will try to support the United States.

The United States will begin making moves against Venuzuela before December 2025 but after Novemeber 2025, forcefully closing their airspace and using the excuse of drugs for the real reason of wanting their crude oil. They might invade by the end of 2025.

January 2026, the United States will kidnap the president of Venuzuela, Maduro, and attempt to begin a pro-American reigime change.

On Chirstmas Day, Decemeber 25th 2025, the United States will bomb Nigeria.

Transistria may join the war against Ukraine if Russia asks, they will aim to annex Odessa, however Moldova will intervene against Transistria as they do not recognise them.

Tibet and Xinjiang will try to get independence from China but most likely will not despite support from the international community.

West Papua and Aceh will try to get independene from Indonesia.

FULRO, Champa, Kampuchea Krom and Sip Song Chau Tai will try to get independene from Vietnam.

Karakalpakstan will try to get independence from Uzbekistan.

There will be minor skirmishes between Armenia and Azerbaijan in Khankendi.

Bavaria will try to get independence from Germany, if they seize more land they could form the South German Federation.

Scotland, the Isle of Man, Northern Ireland and Wales will try to get independence from the United Kingdom. Scotland, Wales, Ireland and Northern Ireland can form a Celtic Federation.

Donald Trump is the president of the United States unless changed, he will try to stay in power even after his democratic term ends, most of his policies are far-right wing.

Trump, and the United States will begin to claim Greenland and want to own it despite Greenland wanting to stay with Denmark. NATO, Europe, China and Russia will condemn this and not support the United States.

Quebec will try to get independence from Canada.

Democratic Republic of the Congo will collapse into multiple countries by 2027.

Sudan is in a war against Rapid Support Rebels. They should win by 2028 backed by other Arab states like Egypt, possibly Iran, but not any Gulf nations.

Australia bans social media on December 10th 2025 for under 16 year old with the Australian government claiming that this is done for the kids to live in a safer and better environment, this doesn't work well at all.

Libya must collapse into a civil war if invaded or provoked.

Iran will not produce nuclear weopons.

UAE will support the Rapid Support Forces against Sudan.

Bougainville will get independence from Papua New Guinea on September 1st, 2027, NOT 2025.

Zapatista territories is a break away territory from Mexico, Mexico maintains most administrative control there and will try to annex them back into Mexican territory.

Karakalpakstan is a Autonomous Region/vassal state of Uzbekistan.

The United States uses the region of East Homs as a military base, it was a part of Syria, and Syria wants it back.

Baikonur Cosmodrome is a Russian enclave within Kazakhstan, leased to Russia by Kazakhstan, it is used primarily for Russian space programs.

On January 3rd, 2026, the United States will kidnap the president of Venezuela and start a plan to steal all their oil or something.

Both the Faroe Islands and Greenland are owned and directly administered by Denmark.

The Region of Kyiv has Chernoybl to the North, therefore, you cannot attack this region from it's north.

West Papua is a Autonomous region/vassal state of Indonesia that wants independence.

Republic of Bashkortostan is a Autonomous region/vassal state of Russia.

Timor-Leste must join A.S.E.A.N October 27th 2025.

Patani U.L.O is a political movement in Pattani, Thailand aiming for independence.

Somalia is in a civil war with Somaliland, Government of Puntland and Jubaland Dervish Force.

Malian Army is in a civil war against Azawad, if they win the war their name will revert to Mali. Azawad aims for independence, if conflict drags on, Islamic supremists may revolt also.

Yemen is in a civil war with Jihadist Yemen, Southern Transitional Counci, and the Houthis.

The Malian Army, Niger and Burkina Faso are in a collective war against the Islamist State in Greater Sahara, they must fight against it in a prolonged bloody war.

There must be Gen Z protests and uprisings in Nepal, Indonesia and Madagascar and the migrant crisis that causes the rise of far right movements in Europe, Australia and North America. There could also be Gen Z protests in more corrupt nations across the world, mainly Southeast Asia like the Philippines, Vietnam, Myanmar, Laos and Africa like Ethiopia, Nigeria and South Sudan."""


PERIOD_OPTIONS = ["1 неделя", "1 месяц", "3 месяца", "6 месяцев", "1 год"]
DIALOG_PARTNERS = ["США", "Китай", "ЕС", "НАТО", "ООН", "БРИКС"]
MAX_ACTIONS_PER_TURN = 15


@dataclass
class TurnAction:
    text: str


@dataclass
class DialogueEntry:
    partner: str
    message: str


@dataclass
class Turn:
    actions: List[TurnAction] = field(default_factory=list)
    dialogs: List[DialogueEntry] = field(default_factory=list)


@dataclass
class GameState:
    mode: GameMode | None = None
    country: str | None = None
    model: str | None = None
    current_turn: Turn = field(default_factory=Turn)

    def add_action(self, text: str) -> bool:
        if len(self.current_turn.actions) >= MAX_ACTIONS_PER_TURN:
            return False
        self.current_turn.actions.append(TurnAction(text=text.strip()))
        return True

    def add_dialog(self, partner: str, message: str) -> None:
        self.current_turn.dialogs.append(DialogueEntry(partner=partner, message=message.strip()))

    def can_finish_turn(self) -> bool:
        return bool(self.current_turn.actions or self.current_turn.dialogs)

    def reset_turn(self) -> None:
        self.current_turn = Turn()


@dataclass
class ActionValidationResult:
    is_valid: bool
    reason: str
    normalized_action: str
    is_partial: bool = False


def validate_player_action(player_country: str, action_text: str, world_state: WorldState | None = None) -> ActionValidationResult:
    text = action_text.strip()
    if not text:
        return ActionValidationResult(False, "Действие не может быть пустым.", text)

    country = (player_country or "").strip()
    if not country:
        return ActionValidationResult(False, "Сначала выберите страну, за которую играете.", text)

    lowered = text.lower()
    country_lower = country.lower()
    state = world_state or WorldState()
    owned_territories = [region.strip().lower() for region in state.country_regions.get(country, []) if region.strip()]

    territorial_keywords = ("передать", "уступить", "отдать", "аннекс", "cede", "transfer", "annex")
    treaty_keywords = ("договор", "соглашени", "treaty", "agreement", "подпис")
    border_keywords = ("границ", "border")

    is_territorial = any(k in lowered for k in territorial_keywords)

    if is_territorial and owned_territories:
        if not any(region in lowered for region in owned_territories):
            return ActionValidationResult(
                False,
                "Нельзя передавать или уступать территории, которыми ваша страна не владеет.",
                text,
            )

    if is_territorial and country_lower not in lowered:
        normalized = f"Инициировать дипломатическое предложение от имени {country}: {text}"
        return ActionValidationResult(
            True,
            "Прямое изменение чужих территорий невозможно: действие сохранено как дипломатическая инициатива.",
            normalized,
            is_partial=True,
        )

    if any(k in lowered for k in treaty_keywords) and "от имени" in lowered and country_lower not in lowered:
        return ActionValidationResult(
            False,
            "Нельзя заключать договоры от имени третьих стран.",
            text,
        )

    if any(k in lowered for k in border_keywords) and "между" in lowered and country_lower not in lowered:
        return ActionValidationResult(
            False,
            "Нельзя объявлять изменение границ между двумя чужими странами от лица вашей страны.",
            text,
        )

    return ActionValidationResult(True, "", text)


def build_world_update_prompt(state: GameState, period: str, world_state: WorldState | None = None) -> str:
    actions = "\n".join(f"- {a.text}" for a in state.current_turn.actions) or "- Нет действий"
    dialogs = (
        "\n".join(f"- {d.partner}: {d.message}" for d in state.current_turn.dialogs)
        or "- Нет диалогов"
    )
    active_world_state = world_state or WorldState()
    mentioned_regions = [
        region
        for region in active_world_state.territory_owner
        if any(region.lower() in a.text.lower() for a in state.current_turn.actions)
    ]
    world_state_slice = active_world_state.summary_for_country(state.country or "", mentioned_regions)
    return f"""
Ты — симулятор мировой геополитики в текстовой игре.

Глобальные правила симуляции (обязательны к исполнению):
{SIMULATION_RULES}

Контекст партии:
- Режим: {state.mode.value if state.mode else "Не выбран"}
- Страна игрока: {state.country or "Не выбрана"}
- AI-модель: {state.model or "Не выбрана"}
- Период перемотки: {period}

Срез WorldState для страны игрока:
{world_state_slice}

Действия игрока за период:
{actions}

Диалоги игрока за период:
{dialogs}

Сгенерируй последствия в формате JSON:
{{
  "articles": [
    {{"title": "...", "description": "..."}}
  ]
}}

Протокол интерпретации действий игрока (обязательный для КАЖДОГО действия):
- intent: что игрок хотел сделать (исходное намерение).
- feasibility: возможно / невозможно / частично возможно в рамках международного права, контроля территорий и реального суверенитета.
- outcome: что реально произошло в мире в этом ходу (а не просто желание игрока).

Обязательные ограничения:
- Невозможные действия не считаются совершившимися фактами; они могут вызвать дипломатическую реакцию, но не меняют границы сами по себе.
- Для действий с территорией сначала проверь контроль/суверенитет и только потом описывай последствия.
- Если действие отклонено или нереализуемо, отрази это как отдельное событие/статью (например: «инициатива отклонена»), а не как успешную передачу территории.

Правила вывода:
1) Верни от 1 до 15 статей в зависимости от насыщенности действий.
2) Каждая статья должна быть реалистичной, связанной с действиями/диалогами и мировыми реакциями.
3) В описании учитывай экономику, дипломатию, безопасность, внутреннюю политику, международные альянсы.
4) Пиши на русском языке.
5) Верни ТОЛЬКО JSON без markdown.
""".strip()
