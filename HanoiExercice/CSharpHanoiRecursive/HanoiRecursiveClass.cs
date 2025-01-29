namespace HanoiTowerRecursive;
public class HanoiRecursiveClass()
{
    private static int Iteration=1;
    public void Move(int DiskNumber, string start, string temp, string goal)
    {
        if (DiskNumber>20)
        {
            Console.WriteLine("Please selection a rational number of Disk to preserve the machine (under 20)");
        }
        else
        {
            if (DiskNumber>0)
            {
                Move(DiskNumber-1, start, goal, temp);
                Console.WriteLine($"{Iteration}: Move disk {DiskNumber-1} from {start} to {goal}");
                Iteration++;
                Move(DiskNumber-1, temp, start, goal);
            }
        }
    }
}
