export type Team = "T" | "CT";

export interface Player {
    id: string;
    name: string;
    x: number;
    y: number;
    team: Team;
    alive: boolean;
}