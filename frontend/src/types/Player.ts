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

export interface PlayerInfo {
    steamid: string;
    name: string;
    team_name: Team;
}

export interface HeatmapData {
    steamid: string;
    team: string;
    round_num: number;
    positions: Array<{ X: number; Y: number }>;
}

export interface RoundInfo {
    round_num: number;
    start_tick: number;
    end_tick: number;
}

export interface RoundsData {
    rounds: RoundInfo[];
}