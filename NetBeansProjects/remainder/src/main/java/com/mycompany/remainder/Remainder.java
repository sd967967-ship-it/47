package com.mycompany.remainder;

import java.util.*;
public class Remainder{
    int a=0;
    int b=0; 
    int rem;
    Scanner in=new Scanner(System.in);
    void input()
    {
        System.out.println("enter the value of dividend");
        a=in.nextInt();
        System.out.print("enter the value of diviser");
        b=in.nextInt();
    }
    void calculate()
    {
        rem=a%b;
    }
    void display()
    {
        System.out.println("the remainder is"+rem);
    }
    public static void main(String args[])
    {
        Remainder ob=new Remainder();
        {
            ob.input();
            ob.calculate();
            ob.display();
        }
    }
}
