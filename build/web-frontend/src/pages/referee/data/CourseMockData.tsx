import type { CourseSection } from "../../../components/Courses/types/CourseTypes";

export const MOCK_LAW_NUMBER = 12;
export const MOCK_LAW_TITLE = 'Fouls & Misconduct';

export const MOCK_COURSE_SECTIONS: CourseSection[] = [
  {
    id: 's1',
    title: 'Types of Free Kicks',
    items: [
      {
        id: 'c1',
        type: 'clause',
        title: 'Direct Free Kick',
        status: 'completed',
        mins: 3,
        clause: {
          n: 1,
          txt: `A direct free kick is awarded to the opposing team when a player commits any of the following offences against an opponent in a manner considered by the referee to be careless, reckless, or using excessive force:\n\n• Charges an opponent\n• Jumps at an opponent\n• Kicks or attempts to kick an opponent\n• Pushes an opponent\n• Strikes or attempts to strike an opponent (including head-butts)\n• Tackles or challenges an opponent\n• Trips or attempts to trip an opponent\n\nA direct free kick is also awarded when a player commits any of the following offences:\n\n• Handles the ball deliberately (except for the goalkeeper within their penalty area)\n• Bites or spits at someone on the team lists or a match official\n• Throws an object at the ball, an opponent, or a match official`,
        },
      },
      {
        id: 'c2',
        type: 'clause',
        title: 'Indirect Free Kick',
        status: 'completed',
        mins: 3,
        clause: {
          n: 2,
          txt: `An indirect free kick is awarded when a player:\n\n• Plays in a dangerous manner\n• Impedes the progress of an opponent without any contact being made\n• Is guilty of dissent, using offensive, insulting or abusive language and/or gestures\n• Prevents the goalkeeper from releasing the ball from their hands\n\nAn indirect free kick is also awarded to the opposing team if a goalkeeper, inside their penalty area, commits any of the following offences:\n\n• Controls the ball with their hand/arm for more than six seconds before releasing it\n• Touches the ball with their hand/arm after releasing it and before it has touched another player\n• Touches the ball with their hand/arm after it has been deliberately kicked to them by a team-mate`,
        },
      },
      {
        id: 'c3',
        type: 'clause',
        title: 'Penalty Kick',
        status: 'completed',
        mins: 2,
        clause: {
          n: 3,
          txt: `A penalty kick is awarded when a player commits a direct free kick offence inside their own penalty area while the ball is in play.\n\nA goal may be scored directly from a penalty kick.\n\nThe ball is placed on the penalty mark. The defending goalkeeper must remain on the goal line, facing the kicker, between the goalposts, without touching the goalposts, crossbar or goal net, until the ball has been kicked.\n\nAll players other than the kicker and goalkeeper must be:\n• At least 9.15 m (10 yds) from the penalty mark\n• Behind the penalty mark\n• Inside the field of play\n• Outside the penalty area`,
        },
      },
      {
        id: 'sc1',
        type: 'scenario',
        title: 'Direct or Indirect?',
        status: 'completed',
        mins: 3,
        scenario: {
          sit: "A goalkeeper inside their own penalty area picks up a deliberate back-pass from a team-mate's foot. What is the correct restart?",
          opts: [
            { id: 'a', t: 'Direct free kick to the opposing team' },
            { id: 'b', t: 'Indirect free kick to the opposing team' },
            { id: 'c', t: 'Drop ball at the position of the goalkeeper' },
            { id: 'd', t: 'No offence — play continues' },
          ],
          cor: 'b',
          expl: `Touching the ball with the hands after it has been deliberately kicked to them by a team-mate is an indirect free kick offence. The goalkeeper cannot handle a deliberate back-pass.`,
        },
      },
    ],
  },
  {
    id: 's2',
    title: 'Disciplinary Actions',
    items: [
      {
        id: 'c4',
        type: 'clause',
        title: 'Yellow Card – Caution',
        status: 'completed',
        mins: 4,
        clause: {
          n: 4,
          txt: `A yellow card is used to communicate that a player, substitute, substituted player, or team official has been cautioned.\n\nA caution is issued for the following offences:\n\n• Delaying the restart of play\n• Dissent by word or action\n• Entering, re-entering, or deliberately leaving the field of play without the referee's permission\n• Failing to respect the required distance when play is restarted with a corner kick, free kick, or throw-in\n• Persistent offences (no specific number of offences constitutes persistent)\n• Unsporting behaviour\n• Entering the referee review area (RRA)\n• Excessively using the 'review' (TV screen) gesture\n\nA player who is cautioned may continue to play. However, a second caution in the same match results in a red card.`,
        },
      },
      {
        id: 'c5',
        type: 'clause',
        title: 'Red Card – Sending Off',
        status: 'completed',
        mins: 4,
        clause: {
          n: 5,
          txt: `A red card is used to communicate that a player has been sent off.\n\nSending-off offences include:\n\n• Denying the opposing team a goal or an obvious goal-scoring opportunity (DOGSO) by a handball offence\n• Denying a goal or an obvious goal-scoring opportunity to an opponent moving towards the player's goal by an offence punishable by a free kick\n• Serious foul play (using excessive force or brutality)\n• Biting or spitting at someone\n• Violent conduct\n• Using offensive, insulting or abusive language and/or gestures\n• Receiving a second caution in the same match\n\nA player who has been sent off must leave the field of play and its immediate surroundings.`,
        },
      },
      {
        id: 'dr1',
        type: 'drill',
        title: 'Card Decisions Drill',
        status: 'completed',
        mins: 4,
        drill: {
          desc: 'For each statement, decide whether it is true or false based on Law 12.',
          items: [
            { s: 'A player who receives a second yellow card in the same match is sent off.', a: 'true' },
            { s: 'Persistent foul play always requires exactly 3 fouls before a caution.', a: 'false' },
            { s: 'Denying an obvious goal-scoring opportunity (DOGSO) always results in a red card.', a: 'false' },
            { s: 'A player can be cautioned for entering the Referee Review Area (RRA).', a: 'true' },
            { s: 'A substitute who has not yet entered the field cannot be shown a red card.', a: 'false' },
          ],
        },
      },
      {
        id: 'sc2',
        type: 'scenario',
        title: 'DOGSO Judgement Call',
        status: 'active',
        mins: 3,
        scenario: {
          sit: 'A defender deliberately handles the ball on the goal line to stop what would have been a certain goal. No other defenders are nearby. What is the correct decision?',
          opts: [
            { id: 'a', t: 'Yellow card + direct free kick to attacking team' },
            { id: 'b', t: 'Red card + penalty kick to attacking team' },
            { id: 'c', t: 'Red card + direct free kick at the position of the offence' },
            { id: 'd', t: 'No card + penalty kick to attacking team' },
          ],
          cor: 'b',
          expl: `This is DOGSO (Denying an Obvious Goal-Scoring Opportunity) via handball inside the penalty area. The offence is punishable by a penalty kick, and since it's a handball DOGSO (not by the goalkeeper in their own area), the player is sent off with a red card.`,
        },
      },
    ],
  },
  {
    id: 's3',
    title: 'Physical Contact & Handling',
    items: [
      {
        id: 'c6',
        type: 'clause',
        title: 'Handling the Ball',
        status: 'locked',
        mins: 4,
        clause: {
          n: 6,
          txt: `It is an offence if a player:\n\n• Deliberately touches the ball with their hand/arm, including moving the hand/arm towards the ball\n• Scores in the opponents' goal directly from their hand/arm, even if accidental\n• Creates a goal-scoring opportunity after the ball has touched their hand/arm, even if accidental\n• Touches the ball with their hand/arm when it has made their body unnaturally bigger\n• Touches the ball with their hand/arm when the hand/arm is above or beyond the shoulder level\n\nNot every touch of a player's hand/arm with the ball is an offence. A player is not guilty of a handball offence if the ball touches their hand/arm:\n\n• Directly from the player's own head or body (including the foot)\n• Directly from the head or body of another player who is close\n• When the hand/arm is close to the body and does not make the body unnaturally bigger`,
        },
      },
      {
        id: 'c7',
        type: 'clause',
        title: 'Violent Conduct',
        status: 'locked',
        mins: 3,
        clause: {
          n: 7,
          txt: `Violent conduct is when a player uses or attempts to use excessive force or brutality against an opponent when not challenging for the ball, or against a team-mate, team official, match official, spectator or any other person, regardless of whether contact is made.\n\nThe key distinctions:\n• Serious foul play: excessive force during a challenge for the ball\n• Violent conduct: excessive force or brutality away from the ball, or deliberate strikes to the head/face`,
        },
      },
      {
        id: 'c8',
        type: 'clause',
        title: 'Careless, Reckless & Excessive Force',
        status: 'locked',
        mins: 4,
        clause: {
          n: 8,
          txt: `Careless: The player has shown a lack of attention or consideration. No disciplinary sanction is needed — only a free kick.\n\nReckless: The player has acted with disregard to the danger to, or consequences for, an opponent. A yellow card is required.\n\nExcessive force / Brutality: The player has far exceeded the necessary use of force and is in danger of injuring their opponent. A red card is required.\n\nReferees must apply the laws consistently throughout the match.`,
        },
      },
      {
        id: 'dr2',
        type: 'drill',
        title: 'Contact Assessment Drill',
        status: 'locked',
        mins: 5,
        drill: {
          desc: 'True or false — classify each challenge description.',
          items: [
            { s: "A player slides in to win the ball and just catches the opponent's ankle with no clear danger intended. This is reckless.", a: 'false' },
            { s: 'A player launches a two-footed lunge at an opponent at high speed. This requires a red card.', a: 'true' },
            { s: 'A careless challenge always results in a yellow card.', a: 'false' },
            { s: 'A reckless challenge requires the referee to show a yellow card.', a: 'true' },
          ],
        },
      },
    ],
  },
  {
    id: 's4',
    title: 'Advantage & Special Cases',
    items: [
      {
        id: 'c9',
        type: 'clause',
        title: 'The Advantage Rule',
        status: 'locked',
        mins: 3,
        clause: {
          n: 9,
          txt: `The referee may allow play to continue when an offence occurs if the non-offending team will benefit from the advantage.\n\nThe advantage should be applied when:\n\n• The non-offending team is in a better position to benefit from play continuing\n• The ball is moving towards the opponent's goal\n• A clear goal-scoring opportunity exists\n\nIf the anticipated advantage does not materialise within a few seconds, the referee may stop play and penalise the original offence.`,
        },
      },
      {
        id: 'c10',
        type: 'clause',
        title: 'Simulation & Deception',
        status: 'locked',
        mins: 3,
        clause: {
          n: 10,
          txt: `A player must not attempt to deceive the referee, for example by feigning injury or pretending to have been fouled (simulation).\n\nSimulation is considered unsporting behaviour and is a cautionable offence, resulting in a yellow card.\n\nPlayers are also prohibited from:\n• Deceiving the referee by using a deliberate trick to pass the ball to the goalkeeper\n• Verbally distracting an opponent during play\n• Making deceptive gestures intended to confuse or mislead the referee`,
        },
      },
      {
        id: 'sc3',
        type: 'scenario',
        title: 'Advantage or Whistle?',
        status: 'locked',
        mins: 3,
        scenario: {
          sit: 'An attacking player is fouled in midfield but retains possession and immediately has a clear run on goal with only the goalkeeper to beat. What should the referee do?',
          opts: [
            { id: 'a', t: 'Stop play immediately and award a direct free kick' },
            { id: 'b', t: 'Play advantage and let the attack develop' },
            { id: 'c', t: 'Stop play and award a penalty kick' },
            { id: 'd', t: 'Play advantage but blow the whistle after 3 seconds regardless' },
          ],
          cor: 'b',
          expl: `The referee should play the advantage here. The non-offending team has a clear goal-scoring opportunity so stopping play would penalise them. If the opportunity breaks down, the referee can revert to the original offence.`,
        },
      },
    ],
  },
];