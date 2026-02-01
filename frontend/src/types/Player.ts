export type Team = "T" | "CT";

export interface Player {
    tick: number;
    steamid: string;
    name: string;
    //team_name: string
    X: number;
    Y: number;
    Z: number;
    //health: number;
    is_alive: boolean;
    //active_weapon: string;
    team_name: Team;
    //alive: boolean;
}